#!/usr/bin/env python3
"""
Advanced Feature Engineer for ML Trading
Generates 50+ technical indicators and statistical features
"""
import numpy as np
import pandas as pd
from collections import deque
from sklearn.feature_selection import mutual_info_regression
import logging

logger = logging.getLogger(__name__)


class AdvancedFeatureEngineer:
    """
    Generates comprehensive feature set for time series prediction
    Includes technical indicators, statistical features, and microstructure metrics
    """
    
    def __init__(self, feature_selection_threshold=0.01):
        self.feature_selection_threshold = feature_selection_threshold
        self.feature_importance_scores = {}
        self.enabled_features = set()  # Features that pass selection
        self.all_feature_names = []
        
    def extract_all_features(self, df, idx, lookback_window=100):
        """
        Extract all 50+ features for given index
        
        Returns:
            numpy array of shape (1, n_features)
        """
        if idx < 20 or idx >= len(df):
            return None
        
        # Get price history
        lookback = min(lookback_window, idx)
        prices = df['price'].iloc[max(0, idx-lookback):idx+1].values
        
        if len(prices) < 10:
            return None
        
        features = {}
        
        # === PRICE-BASED FEATURES ===
        current_price = prices[-1]
        
        # Returns at multiple lags
        for lag in [1, 2, 3, 5, 10, 20, 30]:
            if len(prices) > lag:
                features[f'return_{lag}'] = (prices[-1] - prices[-lag-1]) / prices[-lag-1]
        
        # Log returns
        features['log_return_1'] = np.log(prices[-1] / prices[-2]) if len(prices) > 1 else 0
        
        # === MOVING AVERAGES ===
        for period in [5, 10, 20, 30, 50]:
            if len(prices) >= period:
                ma = np.mean(prices[-period:])
                features[f'sma_{period}'] = ma
                features[f'price_to_sma_{period}'] = (current_price - ma) / ma
        
        # EMA (Exponential Moving Average)
        for period in [5, 10, 20]:
            if len(prices) >= period:
                ema = self._calculate_ema(prices, period)
                features[f'ema_{period}'] = ema
                features[f'price_to_ema_{period}'] = (current_price - ema) / ema
        
        # === VOLATILITY METRICS ===
        for period in [5, 10, 20]:
            if len(prices) >= period:
                returns = np.diff(prices[-period:]) / prices[-period:-1]
                features[f'volatility_{period}'] = np.std(returns)
                features[f'volatility_squared_{period}'] = np.var(returns)
        
        # Parkinson volatility (high-low range based)
        if len(prices) >= 10:
            hl_range = np.max(prices[-10:]) - np.min(prices[-10:])
            features['parkinson_volatility'] = hl_range / np.mean(prices[-10:])
        
        # === MOMENTUM INDICATORS ===
        # ROC (Rate of Change)
        for period in [5, 10, 20]:
            if len(prices) > period:
                features[f'roc_{period}'] = (prices[-1] - prices[-period-1]) / prices[-period-1]
        
        # Momentum (simple difference)
        for period in [3, 5, 10]:
            if len(prices) >= period:
                features[f'momentum_{period}'] = np.mean(np.diff(prices[-period:]))
        
        # Acceleration (second derivative)
        if len(prices) >= 10:
            features['acceleration'] = np.mean(np.diff(np.diff(prices[-10:])))
        
        # === RSI (Relative Strength Index) ===
        for period in [7, 14, 21]:
            rsi = self._calculate_rsi(prices, period)
            if rsi is not None:
                features[f'rsi_{period}'] = rsi
                features[f'rsi_{period}_overbought'] = 1 if rsi > 70 else 0
                features[f'rsi_{period}_oversold'] = 1 if rsi < 30 else 0
        
        # === MACD (Moving Average Convergence Divergence) ===
        macd, signal, histogram = self._calculate_macd(prices)
        if macd is not None:
            features['macd'] = macd
            features['macd_signal'] = signal
            features['macd_histogram'] = histogram
            features['macd_cross_above'] = 1 if histogram > 0 else 0
        
        # === BOLLINGER BANDS ===
        for period in [10, 20]:
            bb_upper, bb_middle, bb_lower, bb_width = self._calculate_bollinger_bands(prices, period)
            if bb_upper is not None:
                features[f'bb_{period}_upper'] = bb_upper
                features[f'bb_{period}_middle'] = bb_middle
                features[f'bb_{period}_lower'] = bb_lower
                features[f'bb_{period}_width'] = bb_width
                features[f'bb_{period}_position'] = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        
        # === ATR (Average True Range) ===
        atr = self._calculate_atr(prices, period=14)
        if atr is not None:
            features['atr_14'] = atr
            features['atr_ratio'] = atr / current_price
        
        # === STATISTICAL FEATURES ===
        # Autocorrelation at multiple lags
        for lag in [1, 5, 10]:
            if len(prices) > lag + 10:
                acf = self._calculate_autocorrelation(prices, lag)
                features[f'autocorr_lag_{lag}'] = acf
        
        # Hurst exponent (mean reversion vs trending)
        if len(prices) >= 50:
            hurst = self._calculate_hurst_exponent(prices[-50:])
            features['hurst_exponent'] = hurst
            features['is_mean_reverting'] = 1 if hurst < 0.5 else 0
            features['is_trending'] = 1 if hurst > 0.5 else 0
        
        # Skewness and Kurtosis
        if len(prices) >= 20:
            returns = np.diff(prices[-20:]) / prices[-20:-1]
            features['skewness'] = self._calculate_skewness(returns)
            features['kurtosis'] = self._calculate_kurtosis(returns)
        
        # === RANGE METRICS ===
        for period in [5, 10, 20]:
            if len(prices) >= period:
                high = np.max(prices[-period:])
                low = np.min(prices[-period:])
                features[f'high_low_range_{period}'] = (high - low) / np.mean(prices[-period:])
                features[f'price_from_high_{period}'] = (high - current_price) / high
                features[f'price_from_low_{period}'] = (current_price - low) / low
        
        # === POSITION IN RECENT RANGE ===
        if len(prices) >= 20:
            high_20 = np.max(prices[-20:])
            low_20 = np.min(prices[-20:])
            features['position_in_range'] = (current_price - low_20) / (high_20 - low_20) if high_20 != low_20 else 0.5
        
        # Convert to array
        self.all_feature_names = sorted(features.keys())
        feature_array = np.array([features.get(name, 0) for name in self.all_feature_names]).reshape(1, -1)
        
        # Replace any NaN or Inf
        feature_array = np.nan_to_num(feature_array, nan=0.0, posinf=1e6, neginf=-1e6)
        
        return feature_array
    
    def _calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD indicator"""
        if len(prices) < slow:
            return None, None, None
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD) - simplified
        signal_line = macd_line  # In full implementation, would calculate EMA of MACD
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices, period=20, num_std=2):
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None, None, None, None
        
        recent_prices = prices[-period:]
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (num_std * std)
        lower = middle - (num_std * std)
        width = upper - lower
        
        return upper, middle, lower, width
    
    def _calculate_atr(self, prices, period=14):
        """Calculate Average True Range"""
        if len(prices) < period + 1:
            return None
        
        # Simplified ATR using high-low range
        ranges = []
        for i in range(len(prices) - period, len(prices)):
            if i > 0:
                tr = prices[i] - prices[i-1]
                ranges.append(abs(tr))
        
        if len(ranges) == 0:
            return 0
        
        return np.mean(ranges)
    
    def _calculate_autocorrelation(self, prices, lag):
        """Calculate autocorrelation at given lag"""
        if len(prices) < lag + 10:
            return 0
        
        returns = np.diff(prices) / prices[:-1]
        if len(returns) <= lag:
            return 0
        
        # Pearson correlation between returns and lagged returns
        x = returns[:-lag]
        y = returns[lag:]
        
        if len(x) == 0 or np.std(x) == 0 or np.std(y) == 0:
            return 0
        
        return np.corrcoef(x, y)[0, 1]
    
    def _calculate_hurst_exponent(self, prices):
        """
        Calculate Hurst exponent
        H < 0.5: Mean reverting
        H = 0.5: Random walk
        H > 0.5: Trending
        """
        if len(prices) < 20:
            return 0.5
        
        lags = range(2, min(20, len(prices) // 2))
        tau = []
        
        for lag in lags:
            # Calculate standard deviation of differences
            differences = np.subtract(prices[lag:], prices[:-lag])
            tau.append(np.std(differences))
        
        # Fit line in log-log space
        if len(tau) < 2:
            return 0.5
        
        log_lags = np.log(list(lags))
        log_tau = np.log(tau)
        
        # Linear regression
        poly = np.polyfit(log_lags, log_tau, 1)
        hurst = poly[0]
        
        # Clamp to reasonable range
        return np.clip(hurst, 0, 1)
    
    def _calculate_skewness(self, data):
        """Calculate skewness of distribution"""
        if len(data) < 3:
            return 0
        
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return 0
        
        skew = np.mean(((data - mean) / std) ** 3)
        return skew
    
    def _calculate_kurtosis(self, data):
        """Calculate kurtosis of distribution"""
        if len(data) < 4:
            return 0
        
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return 0
        
        kurt = np.mean(((data - mean) / std) ** 4) - 3  # Excess kurtosis
        return kurt
    
    def select_features(self, X, y, threshold=None):
        """
        Select features based on mutual information with target
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target vector (n_samples,)
            threshold: Minimum mutual information score
        """
        if threshold is None:
            threshold = self.feature_selection_threshold
        
        if len(X) < 50:
            # Not enough data for feature selection
            self.enabled_features = set(self.all_feature_names)
            return
        
        # Calculate mutual information scores
        mi_scores = mutual_info_regression(X, y, random_state=42)
        
        # Store scores
        for i, feature_name in enumerate(self.all_feature_names):
            self.feature_importance_scores[feature_name] = mi_scores[i]
        
        # Select features above threshold
        self.enabled_features = set()
        for i, score in enumerate(mi_scores):
            if score >= threshold:
                self.enabled_features.add(self.all_feature_names[i])
        
        logger.info(f"Feature selection: {len(self.enabled_features)}/{len(self.all_feature_names)} features selected")
    
    def get_feature_names(self):
        """Get list of all feature names"""
        return self.all_feature_names
    
    def get_selected_features(self):
        """Get list of selected feature names"""
        return sorted(list(self.enabled_features))
