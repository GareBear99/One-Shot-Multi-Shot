#!/usr/bin/env python3
"""
Generate synthetic price data with LEARNABLE patterns
This allows us to validate the ML system actually learns and improves
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_price_data_with_patterns(n_points=10000, base_price=3500):
    """
    Generate synthetic price data with learnable patterns:
    - Trend component (momentum)
    - Mean reversion component
    - Cycle component
    - Some noise
    
    This creates patterns that ML should be able to learn
    """
    # np.random.seed(42)  # Removed - let data vary each run to test learning
    
    timestamps = []
    prices = []
    
    start_time = datetime(2025, 12, 1)
    current_price = base_price
    
    # Pattern parameters
    trend_strength = 0.0001  # Small trend
    mean_reversion_strength = 0.002  # Pull back to mean
    cycle_period = 500  # Cycle every 500 points
    noise_level = 0.0005  # Small noise
    
    for i in range(n_points):
        # Time
        current_time = start_time + timedelta(seconds=i)
        timestamps.append(current_time)
        
        # PATTERN 1: Trend (momentum continues)
        # If price went up recently, likely to continue up (learnable!)
        if i > 10:
            recent_change = prices[-1] - prices[-10]
            trend = recent_change * trend_strength
        else:
            trend = 0
        
        # PATTERN 2: Mean reversion
        # Price pulls back toward moving average (learnable!)
        if i > 20:
            ma_20 = np.mean(prices[-20:])
            mean_reversion = (ma_20 - current_price) * mean_reversion_strength
        else:
            mean_reversion = 0
        
        # PATTERN 3: Cyclical component
        # Regular cycles (learnable!)
        cycle = np.sin(2 * np.pi * i / cycle_period) * 5
        
        # PATTERN 4: Noise (not learnable)
        noise = np.random.randn() * current_price * noise_level
        
        # Combine patterns
        price_change = trend + mean_reversion + cycle + noise
        current_price += price_change
        
        # Prevent negative prices
        current_price = max(100, current_price)
        
        prices.append(current_price)
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'date': timestamps,
        'price': prices,
        'interpolated': [True] * n_points,
        'volume': [1000000] * n_points  # Dummy volume
    })
    
    return df

def analyze_patterns(df):
    """Analyze what patterns exist in the data"""
    prices = df['price'].values
    
    # Calculate returns
    returns = np.diff(prices) / prices[:-1]
    
    # Check for momentum (autocorrelation)
    if len(returns) > 10:
        momentum_corr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
    else:
        momentum_corr = 0
    
    # Check for mean reversion
    if len(prices) > 50:
        # Price vs 20-period MA correlation
        ma_20 = pd.Series(prices).rolling(20).mean().values[20:]
        price_subset = prices[20:]
        distance_from_ma = price_subset - ma_20
        mean_reversion = -np.corrcoef(distance_from_ma[:-1], returns[20:])[0, 1]
    else:
        mean_reversion = 0
    
    print("\n" + "="*80)
    print("SYNTHETIC DATA PATTERN ANALYSIS")
    print("="*80)
    print(f"Data points: {len(df)}")
    print(f"Price range: ${prices.min():.2f} - ${prices.max():.2f}")
    print(f"Momentum correlation: {momentum_corr:.4f} (positive = trending)")
    print(f"Mean reversion strength: {mean_reversion:.4f} (positive = reverts to mean)")
    print("-"*80)
    print("Expected behavior:")
    print("  - ML should learn momentum patterns (predict trend continuation)")
    print("  - ML should learn mean reversion (predict reversals)")
    print("  - Win ratio should improve from ~50% to 55-60%+")
    print("="*80)

if __name__ == "__main__":
    print("Generating synthetic price data with learnable patterns...")
    
    # Generate data
    df = generate_price_data_with_patterns(n_points=10000)
    
    # Save to CSV
    output_file = "minute_data/synthetic_learnable.csv"
    df.to_csv(output_file, index=False)
    print(f"\n✓ Saved to: {output_file}")
    
    # Analyze patterns
    analyze_patterns(df)
    
    print("\nTo test with this data, modify ml_adaptive_trader.py to load:")
    print(f'csv_file = os.path.join(data_dir, "synthetic_learnable.csv")')
