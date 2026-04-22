#!/usr/bin/env python3
"""
High-Frequency Trading Multi-Strategy Backtest
Uses 1-minute granularity data to achieve 256+ trades per day
Target: Maximum profitability with optimal trade frequency
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import json
import glob
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hft_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Fast indicator calculations for HFT"""
    
    @staticmethod
    def calculate_all(df, fast=True):
        """Calculate indicators optimized for minute data"""
        close = df['price']
        
        # Fast moving averages for HFT
        df['sma_5'] = close.rolling(window=5).mean()
        df['sma_10'] = close.rolling(window=10).mean()
        df['sma_20'] = close.rolling(window=20).mean()
        df['ema_5'] = close.ewm(span=5, adjust=False).mean()
        df['ema_10'] = close.ewm(span=10, adjust=False).mean()
        df['ema_20'] = close.ewm(span=20, adjust=False).mean()
        
        # RSI (faster period for HFT)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD (adjusted for minute data)
        df['macd'] = df['ema_5'] - df['ema_10']
        df['macd_signal'] = df['macd'].ewm(span=3, adjust=False).mean()
        
        # Bollinger Bands (tighter for minute data)
        sma = close.rolling(window=20).mean()
        std_dev = close.rolling(window=20).std()
        df['bb_upper'] = sma + (std_dev * 2)
        df['bb_lower'] = sma - (std_dev * 2)
        df['bb_mid'] = sma
        
        # Price momentum
        df['momentum'] = close.pct_change(periods=5) * 100
        
        # Volatility
        df['volatility'] = close.rolling(window=20).std()
        
        return df


class HFTStrategy:
    """Base HFT strategy with minute-level trading"""
    
    def __init__(self, name, initial_balance, position_size_pct, compound=True):
        self.name = name
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position_size_pct = position_size_pct
        self.compound = compound
        self.is_position_open = False
        self.position_entry_price = None
        self.position_quantity = 0
        self.current_trade_type = None
        self.trades = []
        self.tp_price = None
        self.sl_price = None
        
    def get_position_size(self):
        if self.compound:
            return self.balance * self.position_size_pct
        return self.initial_balance * self.position_size_pct
    
    def open_position(self, row, trade_type):
        if not self.is_position_open:
            self.position_entry_price = row['price']
            position_value = self.get_position_size()
            self.position_quantity = position_value / self.position_entry_price
            self.is_position_open = True
            self.current_trade_type = trade_type
            self.set_exit_levels(row)
    
    def close_position(self, row, exit_reason):
        if self.is_position_open:
            exit_price = row['price']
            
            if self.current_trade_type == 'buy':
                profit = (exit_price - self.position_entry_price) * self.position_quantity
            else:
                profit = (self.position_entry_price - exit_price) * self.position_quantity
            
            self.balance += profit
            
            self.trades.append({
                'timestamp': row['timestamp'],
                'strategy': self.name,
                'type': self.current_trade_type,
                'entry_price': self.position_entry_price,
                'exit_price': exit_price,
                'quantity': self.position_quantity,
                'profit': profit,
                'profit_pct': (profit / (self.position_entry_price * self.position_quantity)) * 100,
                'exit_reason': exit_reason,
                'balance_after': self.balance
            })
            
            self.is_position_open = False
            self.position_entry_price = None
            self.position_quantity = 0
            self.current_trade_type = None
    
    def set_exit_levels(self, row):
        pass
    
    def check_entry(self, row):
        return None
    
    def check_exit(self, row):
        return None


class MomentumScalper(HFTStrategy):
    """Ultra-fast scalping on momentum"""
    
    def __init__(self, initial_balance):
        super().__init__("Momentum_Scalper", initial_balance, 0.10, compound=True)
    
    def set_exit_levels(self, row):
        volatility = row['volatility']
        if self.current_trade_type == 'buy':
            self.tp_price = self.position_entry_price + (volatility * 0.5)
            self.sl_price = self.position_entry_price - (volatility * 0.3)
        else:
            self.tp_price = self.position_entry_price - (volatility * 0.5)
            self.sl_price = self.position_entry_price + (volatility * 0.3)
    
    def check_entry(self, row):
        if not self.is_position_open:
            if row['momentum'] > 0.1 and row['rsi'] < 70 and row['ema_5'] > row['ema_10']:
                return 'buy'
            elif row['momentum'] < -0.1 and row['rsi'] > 30 and row['ema_5'] < row['ema_10']:
                return 'sell'
        return None
    
    def check_exit(self, row):
        if self.is_position_open:
            price = row['price']
            if self.current_trade_type == 'buy':
                if price >= self.tp_price:
                    return 'take_profit'
                elif price <= self.sl_price:
                    return 'stop_loss'
            else:
                if price <= self.tp_price:
                    return 'take_profit'
                elif price >= self.sl_price:
                    return 'stop_loss'
        return None


class MeanReversionHFT(HFTStrategy):
    """Mean reversion on 1-minute timeframe"""
    
    def __init__(self, initial_balance):
        super().__init__("MeanRev_HFT", initial_balance, 0.08, compound=True)
    
    def set_exit_levels(self, row):
        self.tp_price = row['bb_mid']
        volatility = row['volatility']
        if self.current_trade_type == 'buy':
            self.sl_price = self.position_entry_price - (volatility * 0.4)
        else:
            self.sl_price = self.position_entry_price + (volatility * 0.4)
    
    def check_entry(self, row):
        if not self.is_position_open:
            if row['price'] < row['bb_lower'] and row['rsi'] < 35:
                return 'buy'
            elif row['price'] > row['bb_upper'] and row['rsi'] > 65:
                return 'sell'
        return None
    
    def check_exit(self, row):
        if self.is_position_open:
            price = row['price']
            if self.current_trade_type == 'buy':
                if price >= self.tp_price or price <= self.sl_price:
                    return 'take_profit' if price >= self.tp_price else 'stop_loss'
            else:
                if price <= self.tp_price or price >= self.sl_price:
                    return 'take_profit' if price <= self.tp_price else 'stop_loss'
        return None


class TrendFollowerHFT(HFTStrategy):
    """Fast trend following for minute data"""
    
    def __init__(self, initial_balance):
        super().__init__("Trend_HFT", initial_balance, 0.07, compound=True)
    
    def set_exit_levels(self, row):
        volatility = row['volatility']
        if self.current_trade_type == 'buy':
            self.tp_price = self.position_entry_price + (volatility * 1.0)
            self.sl_price = self.position_entry_price - (volatility * 0.5)
        else:
            self.tp_price = self.position_entry_price - (volatility * 1.0)
            self.sl_price = self.position_entry_price + (volatility * 0.5)
    
    def check_entry(self, row):
        if not self.is_position_open:
            if (row['ema_5'] > row['ema_10'] > row['ema_20'] and 
                row['macd'] > row['macd_signal'] and row['rsi'] > 50 and row['rsi'] < 75):
                return 'buy'
        return None
    
    def check_exit(self, row):
        if self.is_position_open:
            price = row['price']
            if self.current_trade_type == 'buy':
                if price >= self.tp_price:
                    return 'take_profit'
                elif price <= self.sl_price:
                    return 'stop_loss'
        return None


class RangeTrader(HFTStrategy):
    """Trade range-bound markets"""
    
    def __init__(self, initial_balance):
        super().__init__("Range_Trader", initial_balance, 0.06, compound=True)
    
    def set_exit_levels(self, row):
        volatility = row['volatility']
        if self.current_trade_type == 'buy':
            self.tp_price = row['sma_20']
            self.sl_price = self.position_entry_price - (volatility * 0.4)
        else:
            self.tp_price = row['sma_20']
            self.sl_price = self.position_entry_price + (volatility * 0.4)
    
    def check_entry(self, row):
        if not self.is_position_open:
            # Detect ranging market (low momentum)
            if abs(row['momentum']) < 0.15:
                if row['price'] < row['sma_20'] * 0.998 and row['rsi'] < 40:
                    return 'buy'
                elif row['price'] > row['sma_20'] * 1.002 and row['rsi'] > 60:
                    return 'sell'
        return None
    
    def check_exit(self, row):
        if self.is_position_open:
            price = row['price']
            if self.current_trade_type == 'buy':
                if price >= self.tp_price or price <= self.sl_price:
                    return 'take_profit' if price >= self.tp_price else 'stop_loss'
            else:
                if price <= self.tp_price or price >= self.sl_price:
                    return 'take_profit' if price <= self.tp_price else 'stop_loss'
        return None


class BreakoutHFT(HFTStrategy):
    """Quick breakout trades"""
    
    def __init__(self, initial_balance):
        super().__init__("Breakout_HFT", initial_balance, 0.09, compound=True)
    
    def set_exit_levels(self, row):
        volatility = row['volatility']
        if self.current_trade_type == 'buy':
            self.tp_price = self.position_entry_price + (volatility * 0.8)
            self.sl_price = self.position_entry_price - (volatility * 0.3)
        else:
            self.tp_price = self.position_entry_price - (volatility * 0.8)
            self.sl_price = self.position_entry_price + (volatility * 0.3)
    
    def check_entry(self, row):
        if not self.is_position_open:
            if (row['price'] > row['bb_upper'] and row['momentum'] > 0.2 and 
                row['rsi'] > 55 and row['macd'] > row['macd_signal']):
                return 'buy'
            elif (row['price'] < row['bb_lower'] and row['momentum'] < -0.2 and 
                  row['rsi'] < 45 and row['macd'] < row['macd_signal']):
                return 'sell'
        return None
    
    def check_exit(self, row):
        if self.is_position_open:
            price = row['price']
            if self.current_trade_type == 'buy':
                if price >= self.tp_price:
                    return 'take_profit'
                elif price <= self.sl_price:
                    return 'stop_loss'
            else:
                if price <= self.tp_price:
                    return 'take_profit'
                elif price >= self.sl_price:
                    return 'stop_loss'
        return None


class HFTBacktest:
    """High-frequency backtest engine"""
    
    def __init__(self, capital_per_strategy=2000):
        self.capital_per_strategy = capital_per_strategy
        self.strategies = [
            MomentumScalper(capital_per_strategy),
            MeanReversionHFT(capital_per_strategy),
            TrendFollowerHFT(capital_per_strategy),
            RangeTrader(capital_per_strategy),
            BreakoutHFT(capital_per_strategy)
        ]
        self.all_trades = []
        
    def load_minute_data(self, file_path):
        """Load minute-level CSV data"""
        df = pd.read_csv(file_path, comment='#')
        df['timestamp'] = pd.to_datetime(df['date'])
        df = df[df['interpolated'] == True].copy()
        df = df.dropna(subset=['price'])
        logger.info(f"Loaded {len(df)} minutes of data from {os.path.basename(file_path)}")
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        return df
    
    def run_on_asset(self, df, asset_name):
        """Run all strategies on one asset"""
        logger.info(f"\nCalculating indicators for {asset_name}...")
        df = TechnicalIndicators.calculate_all(df)
        df = df.dropna()
        
        logger.info(f"Running strategies on {asset_name} ({len(df)} candles)...")
        
        for idx, row in df.iterrows():
            for strategy in self.strategies:
                if not strategy.is_position_open:
                    entry_signal = strategy.check_entry(row)
                    if entry_signal:
                        strategy.open_position(row, entry_signal)
                else:
                    exit_signal = strategy.check_exit(row)
                    if exit_signal:
                        strategy.close_position(row, exit_signal)
        
        # Close open positions
        for strategy in self.strategies:
            if strategy.is_position_open:
                strategy.close_position(df.iloc[-1], 'end_of_data')
    
    def run_multi_asset(self, data_dir):
        """Run on multiple assets"""
        csv_files = glob.glob(os.path.join(data_dir, "*_minute.csv"))
        
        logger.info("="*80)
        logger.info("HIGH-FREQUENCY MULTI-STRATEGY BACKTEST")
        logger.info(f"Assets: {len(csv_files)}")
        logger.info(f"Strategies: {len(self.strategies)}")
        logger.info(f"Capital per strategy: ${self.capital_per_strategy:,.2f}")
        logger.info(f"Total capital: ${self.capital_per_strategy * len(self.strategies):,.2f}")
        logger.info("="*80)
        
        for csv_file in csv_files:
            asset_name = os.path.basename(csv_file).replace('_minute.csv', '').upper()
            df = self.load_minute_data(csv_file)
            self.run_on_asset(df, asset_name)
        
        # Collect all trades
        for strategy in self.strategies:
            self.all_trades.extend(strategy.trades)
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive report"""
        if not self.all_trades:
            logger.warning("No trades executed!")
            return None
        
        trades_df = pd.DataFrame(self.all_trades)
        
        total_initial = self.capital_per_strategy * len(self.strategies)
        total_final = sum(s.balance for s in self.strategies)
        total_profit = total_final - total_initial
        total_return = (total_profit / total_initial) * 100
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['profit'] > 0])
        losing_trades = len(trades_df[trades_df['profit'] < 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        avg_win = trades_df[trades_df['profit'] > 0]['profit'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['profit'] < 0]['profit'].mean() if losing_trades > 0 else 0
        
        profit_factor = abs(trades_df[trades_df['profit'] > 0]['profit'].sum() / 
                           trades_df[trades_df['profit'] < 0]['profit'].sum()) if losing_trades > 0 else float('inf')
        
        # Calculate trades per day
        time_span_days = (trades_df['timestamp'].max() - trades_df['timestamp'].min()).total_seconds() / 86400
        trades_per_day = total_trades / time_span_days if time_span_days > 0 else 0
        
        logger.info("\n" + "="*80)
        logger.info("AGGREGATE RESULTS")
        logger.info("="*80)
        logger.info(f"Total Initial Capital:  ${total_initial:,.2f}")
        logger.info(f"Total Final Capital:    ${total_final:,.2f}")
        logger.info(f"Total Profit:           ${total_profit:,.2f}")
        logger.info(f"Total Return:           {total_return:.2f}%")
        logger.info("-"*80)
        logger.info(f"Total Trades:           {total_trades}")
        logger.info(f"Trades Per Day:         {trades_per_day:.1f}")
        logger.info(f"Winning Trades:         {winning_trades}")
        logger.info(f"Losing Trades:          {losing_trades}")
        logger.info(f"Win Rate:               {win_rate:.2f}%")
        logger.info("-"*80)
        logger.info(f"Average Win:            ${avg_win:.2f}")
        logger.info(f"Average Loss:           ${avg_loss:.2f}")
        logger.info(f"Profit Factor:          {profit_factor:.2f}")
        
        logger.info("\n" + "="*80)
        logger.info("PERFORMANCE BY STRATEGY")
        logger.info("="*80)
        
        for strategy in self.strategies:
            if strategy.trades:
                strat_df = pd.DataFrame(strategy.trades)
                strat_profit = strategy.balance - strategy.initial_balance
                strat_return = (strat_profit / strategy.initial_balance) * 100
                strat_win_rate = (len(strat_df[strat_df['profit'] > 0]) / len(strat_df)) * 100
                
                logger.info(f"{strategy.name}:")
                logger.info(f"  Balance: ${strategy.initial_balance:,.2f} → ${strategy.balance:,.2f} ({strat_return:+.2f}%)")
                logger.info(f"  Trades: {len(strategy.trades)} | Win Rate: {strat_win_rate:.1f}%")
        
        logger.info("="*80)
        
        return {
            'total_initial': total_initial,
            'total_final': total_final,
            'total_return': total_return,
            'total_profit': total_profit,
            'total_trades': total_trades,
            'trades_per_day': trades_per_day,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'trades_df': trades_df
        }


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("HIGH-FREQUENCY TRADING BACKTEST")
    print("Minute-Level Data | 5 Strategies | Target: 256+ Trades/Day")
    print("="*80)
    
    data_dir = "/Users/TheRustySpoon/Desktop/Projects/Main projects/Trading_bots/One_Shot/minute_data"
    capital = float(input("\nEnter capital per strategy [default: 2000]: ").strip() or '2000')
    
    backtest = HFTBacktest(capital_per_strategy=capital)
    report = backtest.run_multi_asset(data_dir)
    
    if report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trades_file = f"hft_trades_{timestamp}.csv"
        report['trades_df'].to_csv(trades_file, index=False)
        logger.info(f"\nTrade history saved to: {trades_file}")
        
        summary = {k: v for k, v in report.items() if k != 'trades_df'}
        summary_file = f"hft_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
