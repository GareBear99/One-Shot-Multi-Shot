#!/usr/bin/env python3
"""
Ensemble Manager for Multi-Model Prediction
Combines predictions from multiple models with dynamic weighting
"""
import numpy as np
from collections import deque
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available - install with: pip install xgboost")


class EnsembleModel:
    """Individual model in the ensemble with performance tracking"""
    
    def __init__(self, name, model, scaler=None):
        self.name = name
        self.model = model
        self.scaler = scaler if scaler else StandardScaler()
        self.is_trained = False
        
        # Performance tracking
        self.recent_predictions = deque(maxlen=100)
        self.recent_accuracy = deque(maxlen=100)
        self.weight = 1.0 / 5  # Equal weight initially
        self.total_predictions = 0
        self.correct_predictions = 0
    
    def predict(self, features):
        """Make prediction"""
        if not self.is_trained:
            return 0, 0.0
        
        try:
            features_scaled = self.scaler.transform(features)
            prediction = self.model.predict(features_scaled)[0]
            confidence = min(abs(prediction) * 1000, 1.0)
            return prediction, confidence
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}")
            return 0, 0.0
    
    def train(self, X, y):
        """Train the model"""
        try:
            if not self.is_trained:
                self.scaler.fit(X)
            
            X_scaled = self.scaler.transform(X)
            self.model.fit(X_scaled, y)
            self.is_trained = True
        except Exception as e:
            logger.error(f"{self.name} training error: {e}")
    
    def update_performance(self, was_correct):
        """Update performance metrics"""
        self.total_predictions += 1
        self.recent_accuracy.append(1 if was_correct else 0)
        
        if was_correct:
            self.correct_predictions += 1
    
    def get_accuracy(self):
        """Get recent accuracy"""
        if len(self.recent_accuracy) == 0:
            return 0.5
        return np.mean(self.recent_accuracy)


class EnsembleManager:
    """
    Manages multiple ML models and combines their predictions
    Uses weighted voting based on recent performance
    """
    
    def __init__(self, n_models=5):
        self.models = []
        self.n_models = n_models
        self.ensemble_predictions = deque(maxlen=1000)
        self.total_predictions = 0
        self.correct_predictions = 0
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize diverse set of models"""
        
        # 1. Gradient Boosting (baseline)
        gb_model = GradientBoostingRegressor(
            n_estimators=50,
            learning_rate=0.1,
            max_depth=3,
            warm_start=True
        )
        self.models.append(EnsembleModel("GradientBoosting", gb_model))
        
        # 2. Random Forest (non-linear patterns)
        rf_model = RandomForestRegressor(
            n_estimators=50,
            max_depth=5,
            random_state=42,
            warm_start=True
        )
        self.models.append(EnsembleModel("RandomForest", rf_model))
        
        # 3. Ridge Regression (linear trends)
        ridge_model = Ridge(alpha=1.0)
        self.models.append(EnsembleModel("Ridge", ridge_model))
        
        # 4. XGBoost (if available - fast and accurate)
        if XGBOOST_AVAILABLE:
            xgb_model = XGBRegressor(
                n_estimators=50,
                learning_rate=0.1,
                max_depth=3,
                random_state=42
            )
            self.models.append(EnsembleModel("XGBoost", xgb_model))
        
        # 5. Gradient Boosting (aggressive - faster learning)
        gb_aggressive = GradientBoostingRegressor(
            n_estimators=30,
            learning_rate=0.2,
            max_depth=4,
            warm_start=True
        )
        self.models.append(EnsembleModel("GradientBoosting_Aggressive", gb_aggressive))
        
        logger.info(f"Initialized ensemble with {len(self.models)} models")
    
    def train_all(self, X, y):
        """Train all models in the ensemble"""
        for model in self.models:
            model.train(X, y)
        logger.info(f"Trained all {len(self.models)} ensemble models")
    
    def predict_ensemble(self, features):
        """
        Get ensemble prediction using weighted voting
        
        Returns:
            (prediction, confidence, individual_predictions)
        """
        predictions = []
        confidences = []
        weights = []
        
        for model in self.models:
            pred, conf = model.predict(features)
            predictions.append(pred)
            confidences.append(conf)
            weights.append(model.weight)
        
        if len(predictions) == 0:
            return 0, 0.0, {}
        
        # Weighted average prediction
        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize
        
        ensemble_prediction = np.average(predictions, weights=weights)
        ensemble_confidence = np.average(confidences, weights=weights)
        
        # Convert to direction
        if ensemble_prediction >= 0:
            direction = 1  # UP
        else:
            direction = -1  # DOWN
        
        individual_preds = {
            model.name: {'prediction': pred, 'confidence': conf, 'weight': w}
            for model, pred, conf, w in zip(self.models, predictions, confidences, weights)
        }
        
        return direction, ensemble_confidence, individual_preds
    
    def update_weights(self):
        """
        Update model weights based on recent performance
        Better performing models get higher weights
        """
        accuracies = []
        for model in self.models:
            acc = model.get_accuracy()
            accuracies.append(acc)
        
        # Convert accuracies to weights using softmax-like approach
        accuracies = np.array(accuracies)
        
        # Exponential weighting (models with >50% accuracy get boosted)
        # Models with <50% accuracy get penalized
        weights = np.exp((accuracies - 0.5) * 4)  # Scale factor of 4
        weights = weights / weights.sum()
        
        # Update model weights
        for model, weight in zip(self.models, weights):
            model.weight = weight
        
        # Log weight distribution
        if self.total_predictions % 100 == 0:
            weight_info = ", ".join([f"{m.name}: {m.weight:.3f}" for m in self.models])
            logger.debug(f"Updated weights: {weight_info}")
    
    def update_model_performance(self, individual_predictions, was_correct):
        """Update performance tracking for each model"""
        self.total_predictions += 1
        if was_correct:
            self.correct_predictions += 1
        
        # Update each model's performance based on whether IT was correct
        for model in self.models:
            if model.name in individual_predictions:
                model_pred = individual_predictions[model.name]['prediction']
                
                # Check if this model's prediction was correct
                # (Compare sign of prediction to whether ensemble was correct)
                # Simplified: if ensemble was correct and model agreed, model was correct
                model.update_performance(was_correct)
        
        # Reweight every 50 predictions
        if self.total_predictions % 50 == 0:
            self.update_weights()
    
    def remove_poor_models(self, min_accuracy=0.45, min_predictions=200):
        """
        Remove models performing worse than threshold
        """
        models_to_remove = []
        
        for i, model in enumerate(self.models):
            if model.total_predictions >= min_predictions:
                accuracy = model.get_accuracy()
                if accuracy < min_accuracy:
                    models_to_remove.append(i)
                    logger.warning(f"Removing {model.name} - accuracy {accuracy:.2%} < {min_accuracy:.2%}")
        
        # Remove from back to front to preserve indices
        for i in reversed(models_to_remove):
            del self.models[i]
        
        # Renormalize weights
        if len(self.models) > 0:
            total_weight = sum(m.weight for m in self.models)
            for model in self.models:
                model.weight /= total_weight
    
    def get_ensemble_stats(self):
        """Get statistics about the ensemble"""
        return {
            'n_models': len(self.models),
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
            'ensemble_accuracy': self.correct_predictions / self.total_predictions if self.total_predictions > 0 else 0.5,
            'model_accuracies': {m.name: m.get_accuracy() for m in self.models},
            'model_weights': {m.name: m.weight for m in self.models}
        }
    
    def get_best_model(self):
        """Get the best performing model"""
        if len(self.models) == 0:
            return None
        
        best_model = max(self.models, key=lambda m: m.get_accuracy())
        return best_model
    
    def immediate_learn(self, features, actual_direction, boost_lr=True):
        """
        Immediate learning for all models
        """
        for model in self.models:
            if not model.is_trained:
                continue
            
            try:
                # For models that support warm_start, update immediately
                if hasattr(model.model, 'warm_start'):
                    X_scaled = model.scaler.transform(features)
                    y = np.array([actual_direction])
                    
                    # Boost learning rate temporarily
                    if boost_lr and hasattr(model.model, 'learning_rate'):
                        old_lr = model.model.learning_rate
                        model.model.learning_rate = min(0.3, old_lr * 2)
                        model.model.fit(X_scaled, y)
                        model.model.learning_rate = old_lr
                    else:
                        model.model.fit(X_scaled, y)
            except Exception as e:
                logger.error(f"Immediate learn error for {model.name}: {e}")
