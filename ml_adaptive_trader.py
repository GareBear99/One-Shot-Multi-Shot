#!/usr/bin/env python3
"""
ML-Powered Adaptive Trading System
Learns from every 1-second prediction and continuously optimizes
Uses online learning with immediate feedback loops
"""

import os
import pickle
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime
from collections import deque
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from statistical_validator import StatisticalValidator
from feature_engineer import AdvancedFeatureEngineer
from ensemble_manager import EnsembleManager
from improvement_tracker import ImprovementTracker
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_adaptive_trader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OnlineLearningEngine:
    """
    Online ML model that learns from every prediction
    Updates in real-time as new data arrives
    """
    
    def __init__(self, model_path=None, prediction_cap=1000):
        self.model = GradientBoostingRegressor(
            n_estimators=50,
            learning_rate=0.1,
            max_depth=3,
            warm_start=True  # Allow incremental learning
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.prediction_history = deque(maxlen=1000)
        self.accuracy_history = deque(maxlen=100)
        self.feature_buffer = deque(maxlen=100)
        self.target_buffer = deque(maxlen=100)
        
        # Prediction accumulator with cap
        self.prediction_cap = prediction_cap
        self.pending_predictions = deque(maxlen=prediction_cap)  # Predictions waiting validation
        self.validated_predictions = deque(maxlen=prediction_cap)  # Completed predictions
        
        # Performance tracking
        self.total_predictions = 0
        self.correct_predictions = 0
        self.recent_accuracy = 0.5
        self.real_time_win_ratio = 0.5
        self.win_ratio_history = deque(maxlen=10)  # Track win ratio trends
        
        # Adaptive learning parameters
        self.update_frequency = 10  # Start with update every 10 observations
        self.base_learning_rate = 0.1
        
        # Immediate learning on loss
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.loss_streak_threshold = 3  # Trigger emergency after 3 consecutive losses
        self.emergency_reset_threshold = 5  # Reset model after 5 consecutive losses
        self.failure_threshold = 10  # Flag failure after 10 consecutive losses
        
        # Confidence penalty system
        self.confidence_penalty = 1.0  # Multiplier for prediction confidence (1.0 = no penalty)
        self.min_confidence_penalty = 0.5  # Minimum confidence multiplier
        
        # Wrong prediction counter for batch triggering
        self.wrong_since_last_update = 0
        
        # Auto-inversion detection (if consistently wrong, invert predictions)
        self.prediction_inversion = False  # Toggle to invert predictions
        self.inversion_check_count = 0
        
        # Statistical validator
        self.statistical_validator = StatisticalValidator()
        
        # Improvement tracker - validates system is learning
        self.improvement_tracker = ImprovementTracker(window_size=100)
        
        # Walk-forward validation split (80/20)
        self.use_validation = True
        self.train_val_split = 0.8  # 80% train, 20% validation
        
        # Advanced components
        self.use_ensemble = True  # Toggle ensemble on/off
        self.use_advanced_features = False  # Toggle advanced features (disabled for now - dimension mismatch)
        self.feature_engineer = AdvancedFeatureEngineer() if self.use_advanced_features else None
        self.ensemble_manager = EnsembleManager(n_models=5) if self.use_ensemble else None
        
        # Load existing model if available
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def extract_features(self, df, idx):
        """Extract features for prediction at given index"""
        # Use advanced feature engineer if enabled
        if self.use_advanced_features and self.feature_engineer is not None:
            return self.feature_engineer.extract_all_features(df, idx)
        
        # Fallback to basic features
        if idx < 20:
            return None
        
        row = df.iloc[idx]
        
        # Price-based features
        price = row['price']
        prices = df['price'].iloc[max(0, idx-20):idx].values
        
        if len(prices) < 5:
            return None
        
        features = {
            # Price momentum
            'price_change_1': (price - prices[-1]) / prices[-1] if len(prices) > 0 else 0,
            'price_change_5': (price - prices[-5]) / prices[-5] if len(prices) >= 5 else 0,
            'price_change_10': (price - prices[-10]) / prices[-10] if len(prices) >= 10 else 0,
            
            # Moving averages
            'sma_5': np.mean(prices[-5:]) if len(prices) >= 5 else price,
            'sma_10': np.mean(prices[-10:]) if len(prices) >= 10 else price,
            'sma_20': np.mean(prices[-20:]) if len(prices) >= 20 else price,
            
            # Volatility
            'volatility_5': np.std(prices[-5:]) if len(prices) >= 5 else 0,
            'volatility_10': np.std(prices[-10:]) if len(prices) >= 10 else 0,
            
            # Price position
            'dist_from_sma5': (price - np.mean(prices[-5:])) / np.mean(prices[-5:]) if len(prices) >= 5 else 0,
            'dist_from_sma10': (price - np.mean(prices[-10:])) / np.mean(prices[-10:]) if len(prices) >= 10 else 0,
            
            # Range
            'high_low_range': (np.max(prices[-5:]) - np.min(prices[-5:])) / np.mean(prices[-5:]) if len(prices) >= 5 else 0,
            
            # Momentum indicators
            'momentum_5': np.mean(np.diff(prices[-5:])) if len(prices) >= 5 else 0,
            'acceleration': np.mean(np.diff(np.diff(prices[-10:]))) if len(prices) >= 10 else 0,
        }
        
        return np.array(list(features.values())).reshape(1, -1)
    
    def make_prediction(self, df, idx, timeframe_seconds=1):
        """
        Make a prediction and add to accumulator
        Predict if price will go UP or DOWN in the next timeframe
        Returns: (prediction, confidence)
        """
        features = self.extract_features(df, idx)
        
        if features is None or not self.is_trained:
            return 0, 0.0
        
        try:
            # Normalize features
            features_scaled = self.scaler.transform(features)
            
            # Predict price change
            predicted_change = self.model.predict(features_scaled)[0]
            
            # ALWAYS predict a direction (never neutral - force the model to commit)
            if predicted_change >= 0:
                prediction = 1  # UP (including ties)
            else:
                prediction = -1  # DOWN
            
            # AUTO-INVERSION: If consistently wrong, invert predictions
            if self.prediction_inversion:
                prediction = -prediction
            
            # Confidence based on magnitude with penalty applied
            base_confidence = min(abs(predicted_change) * 1000, 1.0)  # Amplified
            confidence = base_confidence * self.confidence_penalty  # Apply penalty after losses
            
            # Store ALL predictions in accumulator
            self.pending_predictions.append({
                'idx': idx,
                'prediction': prediction,
                'confidence': confidence,
                'entry_price': df.iloc[idx]['price'],
                'target_idx': idx + timeframe_seconds,
                'timestamp': df.iloc[idx]['timestamp'],
                'predicted_change': predicted_change
            })
            
            return prediction, confidence
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return 0, 0.0
    
    def validate_pending_predictions(self, df, current_idx):
        """
        Check pending predictions and validate those that reached their timeframe
        Updates win ratio in real-time
        """
        validated_count = 0
        
        # Check all pending predictions
        to_remove = []
        for i, pred in enumerate(self.pending_predictions):
            # Check if timeframe completed
            if current_idx >= pred['target_idx'] and pred['target_idx'] < len(df):
                # Get actual outcome
                actual_price = df.iloc[pred['target_idx']]['price']
                price_change = actual_price - pred['entry_price']
                
                # Determine actual direction (ignore very small changes)
                price_change_pct = (price_change / pred['entry_price']) * 100
                if abs(price_change_pct) < 0.001:  # Less than 0.001% - consider neutral
                    actual_direction = 0
                elif price_change > 0:
                    actual_direction = 1
                else:
                    actual_direction = -1
                
                # Check if prediction was correct
                # Prediction is correct if direction matches OR price didn't move much
                if actual_direction == 0:
                    was_correct = False  # Don't count neutral moves
                else:
                    was_correct = (pred['prediction'] == actual_direction)
                
                # Add to validated predictions
                self.validated_predictions.append({
                    'prediction': pred['prediction'],
                    'actual': actual_direction,
                    'correct': was_correct,
                    'confidence': pred['confidence'],
                    'price_change_pct': (price_change / pred['entry_price']) * 100
                })
                
                # Update counters
                self.total_predictions += 1
                if was_correct:
                    self.correct_predictions += 1
                    
                    # CORRECT PREDICTION: Reset loss streak, restore confidence
                    self.consecutive_losses = 0
                    self.consecutive_wins += 1
                    # Gradually restore confidence
                    self.confidence_penalty = min(1.0, self.confidence_penalty + 0.05)
                    
                    # Feed to statistical validator
                    self.statistical_validator.add_prediction_outcome(True, pred['confidence'])
                    
                    # Feed to improvement tracker
                    self.improvement_tracker.add_prediction(True)
                else:
                    # WRONG PREDICTION: Immediate learning triggers
                    self.consecutive_wins = 0
                    self.consecutive_losses += 1
                    self.wrong_since_last_update += 1
                    
                    # Apply confidence penalty
                    self.confidence_penalty = max(self.min_confidence_penalty, self.confidence_penalty * 0.9)
                    
                    # Feed to statistical validator
                    self.statistical_validator.add_prediction_outcome(False, pred['confidence'])
                    
                    # Feed to improvement tracker
                    self.improvement_tracker.add_prediction(False)
                    
                    # Extract features for immediate learning
                    features = self.extract_features(df, pred['idx'])
                    
                    # ULTRA-AGGRESSIVE: Immediate learning based on win ratio
                    if self.real_time_win_ratio < 0.40:
                        # <40%: Learn from EVERY wrong prediction (3x boost)
                        logger.info(f"❌ Wrong prediction at {self.real_time_win_ratio:.1%} - IMMEDIATE LEARN (3x)")
                        self._immediate_learn(features, actual_direction, boost_multiplier=3.0)
                        self.wrong_since_last_update = 0
                    elif self.real_time_win_ratio < 0.50:
                        # 40-50%: Learn every 2 wrong predictions (2x boost)
                        if self.wrong_since_last_update >= 2:
                            logger.info(f"❌ 2 wrong predictions at {self.real_time_win_ratio:.1%} - IMMEDIATE LEARN (2x)")
                            self._immediate_learn(features, actual_direction, boost_multiplier=2.0)
                            self.wrong_since_last_update = 0
                    elif self.real_time_win_ratio < 0.55:
                        # 50-55%: Learn every 5 wrong predictions (1.5x boost)
                        if self.wrong_since_last_update >= 5:
                            logger.info(f"❌ 5 wrong predictions at {self.real_time_win_ratio:.1%} - IMMEDIATE LEARN (1.5x)")
                            self._immediate_learn(features, actual_direction, boost_multiplier=1.5)
                            self.wrong_since_last_update = 0
                    
                    # Check for loss streaks
                    if self.consecutive_losses >= self.loss_streak_threshold:
                        self._handle_loss_streak(self.consecutive_losses, df, current_idx)
                
                to_remove.append(i)
                validated_count += 1
        
        # Remove validated predictions from pending
        for i in reversed(to_remove):
            del self.pending_predictions[i]
        
        # Update real-time win ratio
        if len(self.validated_predictions) > 0:
            recent_window = list(self.validated_predictions)[-100:]  # Last 100
            correct_count = sum(1 for p in recent_window if p['correct'])
            self.real_time_win_ratio = correct_count / len(recent_window)
            self.recent_accuracy = self.real_time_win_ratio
            
            # AGGRESSIVE ADJUSTMENT: If win ratio is poor, force immediate model update
            if validated_count > 0 and len(self.validated_predictions) >= 20:
                # Check if we should INVERT predictions (learning opposite pattern)
                if self.real_time_win_ratio < 0.40 and len(self.validated_predictions) >= 200:
                    self.inversion_check_count += 1
                    if self.inversion_check_count >= 50 and not self.prediction_inversion:
                        logger.warning(f"⚠️  ACTIVATING PREDICTION INVERSION - Win ratio {self.real_time_win_ratio:.2%} suggests inverse learning")
                        self.prediction_inversion = True
                        self.inversion_check_count = 0
                
                if self.real_time_win_ratio < 0.45:  # Below 45% - VERY BAD
                    logger.warning(f"Win ratio critically low: {self.real_time_win_ratio:.2%} - FORCING model retrain")
                    self._aggressive_retrain(df, current_idx)
                elif self.real_time_win_ratio < 0.50:  # Below 50% - BAD
                    if validated_count % 5 == 0:  # Force update every 5 validations
                        logger.info(f"Win ratio suboptimal: {self.real_time_win_ratio:.2%} - retraining model")
                        self._force_model_update()
                
                # Turn off inversion if win ratio improves
                if self.prediction_inversion and self.real_time_win_ratio > 0.52:
                    logger.info(f"✓ Deactivating inversion - win ratio improved to {self.real_time_win_ratio:.2%}")
                    self.prediction_inversion = False
                    self.inversion_check_count = 0
        
        return validated_count
    
    def get_prediction_stats(self):
        """Get current prediction statistics"""
        return {
            'pending_predictions': len(self.pending_predictions),
            'validated_predictions': len(self.validated_predictions),
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
            'win_ratio': self.real_time_win_ratio,
            'accuracy_pct': self.real_time_win_ratio * 100
        }
    
    def learn_from_outcome(self, features, actual_movement):
        """
        Learn from the actual outcome
        actual_movement: actual price change (positive or negative)
        """
        if features is None:
            return
        
        # Add to buffer
        self.feature_buffer.append(features)
        self.target_buffer.append(actual_movement)
        
        # ADAPTIVE UPDATE FREQUENCY based on win ratio
        # If performing poorly, update more frequently
        if self.real_time_win_ratio < 0.45:
            update_threshold = 3  # Update every 3 observations when critical
        elif self.real_time_win_ratio < 0.50:
            update_threshold = 5  # Update every 5 when suboptimal
        else:
            update_threshold = self.update_frequency  # Normal frequency
        
        if len(self.feature_buffer) >= update_threshold:
            self._update_model()
    
    def _update_model(self):
        """Update model with buffered data"""
        if len(self.feature_buffer) == 0:
            return
        
        try:
            X = np.vstack(list(self.feature_buffer))
            y = np.array(list(self.target_buffer))
            
            # Fit or update scaler
            if not self.is_trained:
                self.scaler.fit(X)
            
            X_scaled = self.scaler.transform(X)
            
            # Train/update model
            self.model.fit(X_scaled, y)
            self.is_trained = True
            
            # Clear buffers
            self.feature_buffer.clear()
            self.target_buffer.clear()
            
            logger.debug(f"Model updated with {len(y)} samples")
            
        except Exception as e:
            logger.error(f"Model update error: {e}")
    
    def _force_model_update(self):
        """Force immediate model update regardless of buffer size"""
        if len(self.feature_buffer) > 0:
            self._update_model()
    
    def _immediate_learn(self, features, actual_direction, boost_multiplier=3.0):
        """Learn immediately from a single wrong prediction without buffering"""
        if features is None:
            return
        
        try:
            # Save current learning rate
            old_lr = self.model.learning_rate
            
            # Boost learning rate based on how wrong we are
            self.model.learning_rate = min(0.5, self.base_learning_rate * boost_multiplier)
            
            # Normalize features
            if not self.is_trained:
                return  # Can't update if not trained yet
            
            features_scaled = self.scaler.transform(features)
            
            # Update model with single observation
            self.model.fit(features_scaled, np.array([actual_direction]))
            
            logger.debug(f"Immediate learn: LR={self.model.learning_rate:.3f}, actual={actual_direction}")
            
            # Restore learning rate
            self.model.learning_rate = old_lr
            
        except Exception as e:
            logger.error(f"Immediate learn error: {e}")
    
    def _handle_loss_streak(self, streak_length, df=None, current_idx=None):
        """Handle consecutive losses with escalating responses"""
        logger.warning(f"Loss streak detected: {streak_length} consecutive losses")
        
        if streak_length >= self.failure_threshold:
            logger.error(f"MODEL FAILURE: {streak_length} consecutive losses - system needs intervention")
            # In production, this would trigger alerts or fallback to safe mode
            return
        
        if streak_length >= self.emergency_reset_threshold:
            logger.critical(f"EMERGENCY RESET: {streak_length} consecutive losses - resetting model")
            # Reset to warm-up state and retrain from validated predictions
            if len(self.validated_predictions) >= 50:
                # Force aggressive retrain with boosted LR
                old_lr = self.model.learning_rate
                self.model.learning_rate = 0.5
                if len(self.feature_buffer) > 0:
                    self._update_model()
                self.model.learning_rate = old_lr
            return
        
        if streak_length >= self.loss_streak_threshold:
            logger.warning(f"AGGRESSIVE INTERVENTION: {streak_length} consecutive losses - forcing retrain")
            # Force immediate model update with very high learning rate
            old_lr = self.model.learning_rate
            self.model.learning_rate = 0.4
            if len(self.feature_buffer) > 0:
                self._update_model()
            self.model.learning_rate = old_lr
    
    def _aggressive_retrain(self, df, current_idx):
        """Aggressive retraining using recent validated predictions"""
        if len(self.validated_predictions) < 10:
            return
        
        try:
            # Increase learning rate temporarily for faster adaptation
            old_lr = self.model.learning_rate
            self.model.learning_rate = min(0.2, old_lr * 1.5)
            
            # Force buffer flush and update
            if len(self.feature_buffer) > 0:
                self._update_model()
            
            # Restore learning rate
            self.model.learning_rate = old_lr
            
            logger.info(f"Aggressive retrain complete - learning rate temporarily boosted")
            
        except Exception as e:
            logger.error(f"Aggressive retrain error: {e}")
    
    def record_prediction_accuracy(self, was_correct):
        """Track prediction accuracy"""
        self.total_predictions += 1
        if was_correct:
            self.correct_predictions += 1
        
        self.accuracy_history.append(1 if was_correct else 0)
        self.recent_accuracy = np.mean(self.accuracy_history) if len(self.accuracy_history) > 0 else 0.5
    
    def save_model(self, path):
        """Save COMPLETE model state including all learning variables"""
        state = {
            # Core model
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
            
            # Prediction tracking
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
            'recent_accuracy': self.recent_accuracy,
            'real_time_win_ratio': self.real_time_win_ratio,
            'win_ratio_history': list(self.win_ratio_history),
            
            # Learning state
            'consecutive_losses': self.consecutive_losses,
            'consecutive_wins': self.consecutive_wins,
            'confidence_penalty': self.confidence_penalty,
            'wrong_since_last_update': self.wrong_since_last_update,
            
            # Auto-inversion state
            'prediction_inversion': self.prediction_inversion,
            'inversion_check_count': self.inversion_check_count,
            
            # Adaptive parameters
            'update_frequency': self.update_frequency,
            'base_learning_rate': self.base_learning_rate,
            
            # Validated predictions (keep last 1000)
            'validated_predictions': list(self.validated_predictions),
            
            # Statistical validator state
            'stat_validator_outcomes': list(self.statistical_validator.prediction_outcomes),
            'stat_validator_returns': list(self.statistical_validator.prediction_returns),
            
            # Improvement tracker state
            'improvement_segments': self.improvement_tracker.segments,
            'improvement_current_segment': self.improvement_tracker.current_segment_predictions,
            'improvement_total_predictions': self.improvement_tracker.total_predictions,
            'improvement_total_correct': self.improvement_tracker.total_correct,
            'improvement_trend': self.improvement_tracker.improvement_trend,
            'improvement_consecutive_improvements': self.improvement_tracker.consecutive_improvements,
            'improvement_consecutive_degradations': self.improvement_tracker.consecutive_degradations,
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)
        logger.info(f"Model saved to {path} with complete learning state")
        logger.info(f"  Total predictions: {self.total_predictions}, Win ratio: {self.real_time_win_ratio:.2%}")
        logger.info(f"  Inversion active: {self.prediction_inversion}, Confidence penalty: {self.confidence_penalty:.3f}")
    
    def load_model(self, path):
        """Load COMPLETE model state including all learning variables"""
        try:
            with open(path, 'rb') as f:
                state = pickle.load(f)
            
            # Core model (always present)
            self.model = state['model']
            self.scaler = state['scaler']
            self.is_trained = state['is_trained']
            
            # Prediction tracking (with backward compatibility)
            self.total_predictions = state.get('total_predictions', 0)
            self.correct_predictions = state.get('correct_predictions', 0)
            self.recent_accuracy = state.get('recent_accuracy', 0.5)
            self.real_time_win_ratio = state.get('real_time_win_ratio', 0.5)
            self.win_ratio_history = deque(state.get('win_ratio_history', []), maxlen=10)
            
            # Learning state (with backward compatibility)
            self.consecutive_losses = state.get('consecutive_losses', 0)
            self.consecutive_wins = state.get('consecutive_wins', 0)
            self.confidence_penalty = state.get('confidence_penalty', 1.0)
            self.wrong_since_last_update = state.get('wrong_since_last_update', 0)
            
            # Auto-inversion state (with backward compatibility)
            self.prediction_inversion = state.get('prediction_inversion', False)
            self.inversion_check_count = state.get('inversion_check_count', 0)
            
            # Adaptive parameters (with backward compatibility)
            self.update_frequency = state.get('update_frequency', 10)
            self.base_learning_rate = state.get('base_learning_rate', 0.1)
            
            # Validated predictions (with backward compatibility)
            self.validated_predictions = deque(state.get('validated_predictions', []), maxlen=self.prediction_cap)
            
            # Statistical validator state (with backward compatibility)
            self.statistical_validator.prediction_outcomes = deque(state.get('stat_validator_outcomes', []), maxlen=1000)
            self.statistical_validator.prediction_returns = deque(state.get('stat_validator_returns', []), maxlen=1000)
            
            # Improvement tracker state (with backward compatibility)
            self.improvement_tracker.segments = state.get('improvement_segments', [])
            self.improvement_tracker.current_segment_predictions = state.get('improvement_current_segment', [])
            self.improvement_tracker.total_predictions = state.get('improvement_total_predictions', 0)
            self.improvement_tracker.total_correct = state.get('improvement_total_correct', 0)
            self.improvement_tracker.improvement_trend = state.get('improvement_trend', 0.0)
            self.improvement_tracker.consecutive_improvements = state.get('improvement_consecutive_improvements', 0)
            self.improvement_tracker.consecutive_degradations = state.get('improvement_consecutive_degradations', 0)
            
            # Check if this is an old model
            is_old_model = 'recent_accuracy' not in state
            if is_old_model:
                logger.warning(f"Loaded OLD model format from {path} - some learning state will be reset")
            else:
                logger.info(f"Model loaded from {path} with complete learning state")
            
            logger.info(f"  Total predictions: {self.total_predictions}, Win ratio: {self.real_time_win_ratio:.2%}")
            logger.info(f"  Inversion active: {self.prediction_inversion}, Confidence penalty: {self.confidence_penalty:.3f}")
            logger.info(f"  Improvement segments: {len(self.improvement_tracker.segments)}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            import traceback
            logger.error(traceback.format_exc())


class AdaptiveStrategy:
    """
    Trading strategy that adapts based on ML predictions
    Adjusts position sizes and entry criteria based on model confidence
    """
    
    def __init__(self, name, initial_balance, ml_engine):
        self.name = name
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.ml_engine = ml_engine
        
        # Position tracking
        self.is_position_open = False
        self.position_entry_price = None
        self.position_entry_idx = None
        self.position_type = None  # 'long' or 'short'
        self.position_size = 0
        
        # Adaptive parameters (learn optimal values)
        self.position_size_base = 0.05  # Start conservative
        self.confidence_threshold = 0.3  # Minimum confidence to trade
        self.max_hold_time = 60  # Max seconds to hold position
        
        # Performance tracking
        self.trades = []
        self.wins = 0
        self.losses = 0
        
        # Parameter optimization history
        self.param_performance = {
            'position_sizes': deque(maxlen=50),
            'confidence_thresholds': deque(maxlen=50),
            'outcomes': deque(maxlen=50)
        }
    
    def should_enter_trade(self, prediction, confidence, current_idx):
        """Decide if we should enter a trade"""
        if self.is_position_open:
            return False
        
        # Only trade if model is confident enough
        if confidence < self.confidence_threshold:
            return False
        
        # Only trade on strong predictions
        if prediction == 0:
            return False
        
        # Adjust confidence threshold based on recent accuracy
        if self.ml_engine.recent_accuracy > 0.6:
            # Model is performing well, can be more aggressive
            self.confidence_threshold = max(0.2, self.confidence_threshold - 0.01)
        elif self.ml_engine.recent_accuracy < 0.45:
            # Model struggling, be more conservative
            self.confidence_threshold = min(0.5, self.confidence_threshold + 0.01)
        
        return True
    
    def calculate_position_size(self, confidence):
        """Calculate position size based on confidence and recent performance"""
        # Base size adjusted by confidence
        size_multiplier = 1 + confidence  # 1.0 to 2.0
        
        # Adjust based on recent win rate
        if len(self.trades) > 10:
            recent_trades = self.trades[-10:]
            recent_wins = sum(1 for t in recent_trades if t['profit'] > 0)
            win_rate = recent_wins / len(recent_trades)
            
            if win_rate > 0.6:
                size_multiplier *= 1.2  # Increase size when winning
            elif win_rate < 0.4:
                size_multiplier *= 0.8  # Decrease size when losing
        
        position_size = self.balance * self.position_size_base * size_multiplier
        return min(position_size, self.balance * 0.15)  # Cap at 15%
    
    def enter_position(self, row, idx, prediction, confidence):
        """Open a position"""
        if self.is_position_open:
            return
        
        self.position_entry_price = row['price']
        self.position_entry_idx = idx
        self.position_type = 'long' if prediction > 0 else 'short'
        
        position_value = self.calculate_position_size(confidence)
        self.position_size = position_value / self.position_entry_price
        
        self.is_position_open = True
        
        logger.debug(f"{self.name}: Opened {self.position_type} at {self.position_entry_price:.6f} "
                    f"(size: ${position_value:.2f}, confidence: {confidence:.2f})")
    
    def should_exit_position(self, row, idx, prediction):
        """Decide if we should exit current position"""
        if not self.is_position_open:
            return False
        
        current_price = row['price']
        hold_time = idx - self.position_entry_idx
        
        # Calculate current P&L
        if self.position_type == 'long':
            pnl_pct = (current_price - self.position_entry_price) / self.position_entry_price
        else:
            pnl_pct = (self.position_entry_price - current_price) / self.position_entry_price
        
        # Exit conditions
        # 1. Hit profit target (adaptive)
        profit_target = 0.002 if self.ml_engine.recent_accuracy > 0.55 else 0.003
        if pnl_pct >= profit_target:
            return True, 'take_profit'
        
        # 2. Hit stop loss (adaptive)
        stop_loss = -0.001 if self.ml_engine.recent_accuracy > 0.55 else -0.0015
        if pnl_pct <= stop_loss:
            return True, 'stop_loss'
        
        # 3. Model predicts reversal
        if prediction != 0:
            if (self.position_type == 'long' and prediction < 0) or \
               (self.position_type == 'short' and prediction > 0):
                return True, 'reversal_signal'
        
        # 4. Max hold time
        if hold_time >= self.max_hold_time:
            return True, 'max_hold_time'
        
        return False, None
    
    def exit_position(self, row, idx, reason):
        """Close position and record trade"""
        if not self.is_position_open:
            return
        
        exit_price = row['price']
        
        if self.position_type == 'long':
            profit = (exit_price - self.position_entry_price) * self.position_size
        else:
            profit = (self.position_entry_price - exit_price) * self.position_size
        
        self.balance += profit
        
        # Record trade
        trade = {
            'timestamp': row['timestamp'],
            'strategy': self.name,
            'type': self.position_type,
            'entry_price': self.position_entry_price,
            'exit_price': exit_price,
            'profit': profit,
            'profit_pct': (profit / (self.position_entry_price * self.position_size)) * 100,
            'hold_time': idx - self.position_entry_idx,
            'exit_reason': reason,
            'balance_after': self.balance,
            'ml_accuracy': self.ml_engine.recent_accuracy
        }
        
        self.trades.append(trade)
        
        if profit > 0:
            self.wins += 1
        else:
            self.losses += 1
        
        # Record parameter performance for optimization
        self.param_performance['position_sizes'].append(self.position_size_base)
        self.param_performance['confidence_thresholds'].append(self.confidence_threshold)
        self.param_performance['outcomes'].append(profit)
        
        logger.debug(f"{self.name}: Closed {self.position_type} at {exit_price:.6f} "
                    f"(P&L: ${profit:.2f}, reason: {reason})")
        
        # Reset position
        self.is_position_open = False
        self.position_entry_price = None
        self.position_entry_idx = None
        self.position_type = None
        self.position_size = 0
        
        # Optimize parameters after each trade
        self._optimize_parameters()
    
    def _optimize_parameters(self):
        """Adjust strategy parameters based on recent performance"""
        if len(self.param_performance['outcomes']) < 10:
            return
        
        recent_outcomes = list(self.param_performance['outcomes'])[-10:]
        avg_profit = np.mean(recent_outcomes)
        
        # Adjust position size
        if avg_profit > 0:
            # Winning - gradually increase position size
            self.position_size_base = min(0.10, self.position_size_base * 1.02)
        else:
            # Losing - decrease position size
            self.position_size_base = max(0.02, self.position_size_base * 0.95)
        
        logger.debug(f"{self.name}: Optimized params - pos_size: {self.position_size_base:.3f}, "
                    f"conf_threshold: {self.confidence_threshold:.3f}")


class MLAdaptiveBacktest:
    """
    Backtesting engine with continuous online learning
    Model learns from every prediction and adapts in real-time
    """
    
    def __init__(self, initial_balance=10000, num_strategies=5, load_latest_model=True):
        self.initial_balance = initial_balance
        
        # Create ML engine
        self.ml_engine = OnlineLearningEngine()
        
        # Load latest model if exists
        if load_latest_model:
            self._load_latest_model()
        
        # Create multiple adaptive strategies
        self.strategies = [
            AdaptiveStrategy(f"Adaptive_Strategy_{i+1}", 
                           initial_balance / num_strategies, 
                           self.ml_engine)
            for i in range(num_strategies)
        ]
        
        self.all_trades = []
        self.learning_log = []
    
    def _load_latest_model(self):
        """Load the most recent saved model to continue learning"""
        import glob
        model_files = glob.glob("ml_model_*.pkl")
        
        if model_files:
            # Get the most recent model file
            latest_model = max(model_files, key=lambda x: os.path.getmtime(x))
            try:
                self.ml_engine.load_model(latest_model)
                logger.info(f"✓ Loaded previous model: {latest_model}")
                logger.info(f"  Previous total predictions: {self.ml_engine.total_predictions}")
                logger.info(f"  Previous win ratio: {self.ml_engine.real_time_win_ratio:.2%}")
            except Exception as e:
                logger.warning(f"Could not load model: {e}")
    
    def run_backtest(self, df, asset_name):
        """
        Run backtest with online learning
        Learn from EVERY prediction, not just trades
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Running adaptive backtest on {asset_name}")
        logger.info(f"Data points: {len(df)}")
        logger.info(f"{'='*80}")
        
        # Warm-up period: train initial models
        warmup_size = min(100, len(df) // 4)
        logger.info(f"Warm-up phase: training on first {warmup_size} data points...")
        
        # Collect warm-up data
        X_warmup = []
        y_warmup = []
        
        for idx in range(20, warmup_size):
            features = self.ml_engine.extract_features(df, idx)
            if features is not None and idx < len(df) - 1:
                actual_movement = df.iloc[idx + 1]['price'] - df.iloc[idx]['price']
                X_warmup.append(features)
                y_warmup.append(actual_movement)
                self.ml_engine.learn_from_outcome(features, actual_movement)
        
        # Train base model
        self.ml_engine._update_model()
        
        # Train ensemble if enabled
        if self.ml_engine.use_ensemble and self.ml_engine.ensemble_manager is not None:
            if len(X_warmup) > 10:
                X_array = np.vstack(X_warmup)
                y_array = np.array(y_warmup)
                self.ml_engine.ensemble_manager.train_all(X_array, y_array)
                logger.info("Ensemble models trained")
        
        logger.info(f"Warm-up complete. Starting live trading with online learning...")
        
        # Live trading with continuous learning
        for idx in range(warmup_size, len(df) - 1):
            row = df.iloc[idx]
            next_row = df.iloc[idx + 1]
            
            # ===== PREDICTION ACCUMULATOR PHASE (EVERY SECOND) =====
            # 1. MAKE prediction and add to accumulator
            prediction, confidence = self.ml_engine.make_prediction(df, idx, timeframe_seconds=1)
            
            # 2. VALIDATE pending predictions that reached their timeframe
            validated_count = self.ml_engine.validate_pending_predictions(df, idx)
            
            # 3. LEARN from actual movement (continuous online learning)
            actual_movement = next_row['price'] - row['price']
            actual_direction = 1 if actual_movement > 0 else (-1 if actual_movement < 0 else 0)
            
            features = self.ml_engine.extract_features(df, idx)
            if features is not None:
                self.ml_engine.learn_from_outcome(features, actual_movement)
            
            # ===== TRADING PHASE =====
            # 4. TRADE based on predictions and ML confidence
            for strategy in self.strategies:
                # Check if should exit existing position
                if strategy.is_position_open:
                    should_exit, reason = strategy.should_exit_position(row, idx, prediction)
                    if should_exit:
                        strategy.exit_position(row, idx, reason)
                
                # Check if should enter new position
                elif strategy.should_enter_trade(prediction, confidence, idx):
                    strategy.enter_position(row, idx, prediction, confidence)
            
            # Log learning progress and prediction stats periodically
            if idx % 500 == 0:
                stats = self.ml_engine.get_prediction_stats()
                logger.info(f"Progress: {idx}/{len(df)} | "
                          f"Win Ratio: {stats['win_ratio']:.2%} | "
                          f"Pending: {stats['pending_predictions']} | "
                          f"Validated: {stats['validated_predictions']} | "
                          f"Total: {stats['total_predictions']}")
        
        # Close any open positions
        last_row = df.iloc[-1]
        for strategy in self.strategies:
            if strategy.is_position_open:
                strategy.exit_position(last_row, len(df)-1, 'end_of_data')
        
        # Collect all trades
        for strategy in self.strategies:
            self.all_trades.extend(strategy.trades)
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive performance report"""
        # Get prediction stats first (even if no trades)
        pred_stats = self.ml_engine.get_prediction_stats()
        stat_report = self.ml_engine.statistical_validator.get_comprehensive_report()
        
        # Print prediction and statistical validation (always)
        logger.info("\n" + "="*80)
        logger.info("ML ADAPTIVE TRADING RESULTS")
        logger.info("="*80)
        logger.info("PREDICTION ACCUMULATOR STATS (SECOND-BY-SECOND)")
        logger.info("-"*80)
        logger.info(f"Real-Time Win Ratio:        {pred_stats['win_ratio']:.2%}")
        logger.info(f"Total Predictions Made:     {pred_stats['total_predictions']}")
        logger.info(f"Validated Predictions:      {pred_stats['validated_predictions']}")
        logger.info(f"Correct Predictions:        {pred_stats['correct_predictions']}")
        logger.info(f"Pending Predictions:        {pred_stats['pending_predictions']}")
        logger.info("-"*80)
        logger.info("STATISTICAL VALIDATION")
        logger.info("-"*80)
        logger.info(f"Statistically Significant:  {'✓ YES' if stat_report['is_statistically_significant'] else '✗ NO'}")
        logger.info(f"p-value:                    {stat_report['p_value']:.4f} (threshold: 0.05)")
        logger.info(f"Sharpe Ratio:               {stat_report['sharpe_ratio']:.2f} {'✓' if stat_report['passes_sharpe'] else '✗'} (target: >1.0)")
        logger.info(f"Information Coefficient:    {stat_report['information_coefficient']:.3f} {'✓' if stat_report['passes_ic'] else '✗'} (target: >0.05)")
        logger.info(f"95% Confidence Interval:    [{stat_report['confidence_interval'][0]:.2%}, {stat_report['confidence_interval'][1]:.2%}]")
        logger.info(f"Overall Confidence:         {stat_report['overall_confidence']}")
        logger.info("-"*80)
        
        # Improvement tracking report
        improvement_status = self.ml_engine.improvement_tracker.get_improvement_status()
        logger.info("CONTINUOUS IMPROVEMENT TRACKING")
        logger.info("-"*80)
        logger.info(f"Learning Status:            {improvement_status['status']}")
        if improvement_status['status'] != 'INSUFFICIENT_DATA':
            logger.info(f"Improvement Trend:          {improvement_status['trend']:+.4f} per 100 predictions")
            logger.info(f"First 300 predictions:      {improvement_status['first_3_segments']:.2%}")
            logger.info(f"Recent 300 predictions:     {improvement_status['recent_win_ratio']:.2%}")
            logger.info(f"Overall Improvement:        {improvement_status['improvement_delta']:+.2%}")
            logger.info(f"Is Improving:               {'YES ✓' if improvement_status['is_improving'] else 'NO ✗'}")
            
            # Should continue trading?
            should_continue, reason = self.ml_engine.improvement_tracker.should_continue_trading()
            if should_continue:
                logger.info(f"Recommendation:             ✓ CONTINUE - {reason}")
            else:
                logger.warning(f"Recommendation:             ✗ STOP - {reason}")
        else:
            logger.info(f"Status:                     {improvement_status['message']}")
        logger.info("-"*80)
        
        if not self.all_trades:
            logger.warning("No trades executed!")
            logger.info("="*80)
            return None
        
        trades_df = pd.DataFrame(self.all_trades)
        
        total_initial = sum(s.initial_balance for s in self.strategies)
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
        
        logger.info("TRADING RESULTS")
        logger.info("-"*80)
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
        logger.info("="*80)
        
        return {
            'total_return': total_return,
            'total_profit': total_profit,
            'total_trades': total_trades,
            'trades_per_day': trades_per_day,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'prediction_win_ratio': pred_stats['win_ratio'],
            'prediction_accuracy_pct': pred_stats['accuracy_pct'],
            'total_predictions': pred_stats['total_predictions'],
            'validated_predictions': pred_stats['validated_predictions'],
            'correct_predictions': pred_stats['correct_predictions'],
            'pending_predictions': pred_stats['pending_predictions'],
            'trades_df': trades_df
        }


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("ML ADAPTIVE TRADING SYSTEM")
    print("Learns from Every Second | Continuous Online Learning")
    print("="*80)
    
    # Load minute data
    data_dir = "/Users/TheRustySpoon/Desktop/Projects/Main projects/Trading_bots/One_Shot/minute_data"
    # Use synthetic learnable data to validate ML learning
    csv_file = os.path.join(data_dir, "synthetic_learnable.csv")
    
    logger.info(f"Loading data from {csv_file}...")
    df = pd.read_csv(csv_file, comment='#')
    df['timestamp'] = pd.to_datetime(df['date'])
    df = df[df['interpolated'] == True].copy()
    df = df.dropna(subset=['price'])
    df = df.reset_index(drop=True)
    
    logger.info(f"Loaded {len(df)} data points")
    logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Run adaptive backtest
    initial_capital = float(input("\nEnter initial capital [default: 10000]: ").strip() or '10000')
    num_strategies = int(input("Enter number of strategies [default: 5]: ").strip() or '5')
    
    backtest = MLAdaptiveBacktest(initial_balance=initial_capital, num_strategies=num_strategies)
    report = backtest.run_backtest(df, "ETH")
    
    # Save results
    if report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        trades_file = f"ml_adaptive_trades_{timestamp}.csv"
        report['trades_df'].to_csv(trades_file, index=False)
        logger.info(f"\nTrade history saved to: {trades_file}")
        
        summary = {k: v for k, v in report.items() if k != 'trades_df'}
        summary_file = f"ml_adaptive_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"Summary saved to: {summary_file}")
        
        # Save ML model
        model_file = f"ml_model_{timestamp}.pkl"
        backtest.ml_engine.save_model(model_file)


if __name__ == "__main__":
    main()
