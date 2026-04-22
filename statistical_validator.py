#!/usr/bin/env python3
"""
Statistical Validator for ML Trading Predictions
Provides rigorous mathematical validation of model performance
"""
import numpy as np
from scipy import stats
from collections import deque
import logging

logger = logging.getLogger(__name__)


class StatisticalValidator:
    """
    Validates ML predictions using statistical tests and financial metrics
    """
    
    def __init__(self, significance_level=0.05):
        self.significance_level = significance_level
        
        # Track prediction outcomes for statistical tests
        self.prediction_outcomes = deque(maxlen=1000)  # 1=correct, 0=wrong
        self.prediction_returns = deque(maxlen=1000)  # +1 for correct, -1 for wrong
        
        # Calibration tracking
        self.calibration_bins = 10
        self.calibration_data = {i: {'predicted': [], 'actual': []} for i in range(self.calibration_bins)}
        
        # Overfitting detection
        self.train_accuracy_history = deque(maxlen=100)
        self.val_accuracy_history = deque(maxlen=100)
    
    def add_prediction_outcome(self, was_correct, confidence=None):
        """Add a prediction outcome for statistical analysis"""
        self.prediction_outcomes.append(1 if was_correct else 0)
        self.prediction_returns.append(1.0 if was_correct else -1.0)
        
        # Track calibration if confidence provided
        if confidence is not None:
            bin_idx = min(int(confidence * self.calibration_bins), self.calibration_bins - 1)
            self.calibration_data[bin_idx]['predicted'].append(confidence)
            self.calibration_data[bin_idx]['actual'].append(1 if was_correct else 0)
    
    def binomial_test(self, min_predictions=30):
        """
        Test if win ratio is statistically significantly better than random (50%)
        
        H0: p = 0.5 (random guessing)
        H1: p > 0.5 (better than random)
        
        Returns:
            (is_significant, p_value, z_score, win_ratio)
        """
        n = len(self.prediction_outcomes)
        
        if n < min_predictions:
            return False, 1.0, 0.0, 0.5
        
        x = sum(self.prediction_outcomes)  # Number of correct predictions
        win_ratio = x / n
        
        # Z-test for proportion
        p0 = 0.5  # Null hypothesis: random guessing
        
        # Test statistic: Z = (p_hat - p0) / sqrt(p0(1-p0)/n)
        se = np.sqrt(p0 * (1 - p0) / n)
        z_score = (win_ratio - p0) / se
        
        # One-tailed test (we only care if it's better than random)
        p_value = 1 - stats.norm.cdf(z_score)
        
        is_significant = p_value < self.significance_level
        
        return is_significant, p_value, z_score, win_ratio
    
    def sharpe_ratio(self):
        """
        Calculate Sharpe ratio of predictions
        
        Sharpe = E[returns] / std(returns)
        where returns = +1 for correct, -1 for wrong
        
        Target: Sharpe > 1.0
        """
        if len(self.prediction_returns) < 10:
            return 0.0
        
        returns = np.array(self.prediction_returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        sharpe = mean_return / std_return
        
        # Annualize assuming 252 trading days, ~1000 predictions per day
        sharpe_annualized = sharpe * np.sqrt(252 * 1000)
        
        return sharpe_annualized
    
    def information_coefficient(self):
        """
        Calculate Information Coefficient (IC)
        
        IC = correlation(predicted_direction, actual_direction)
        
        Target: IC > 0.05 (5% correlation is significant in finance)
        """
        if len(self.prediction_outcomes) < 30:
            return 0.0
        
        # For binary predictions, IC is related to accuracy
        # IC approximation: 2 * (accuracy - 0.5)
        accuracy = np.mean(self.prediction_outcomes)
        ic = 2 * (accuracy - 0.5)
        
        return ic
    
    def calibration_score(self):
        """
        Check if predicted probabilities match actual outcomes
        
        Returns calibration error (lower is better, 0 = perfect calibration)
        """
        calibration_errors = []
        
        for bin_idx in range(self.calibration_bins):
            bin_data = self.calibration_data[bin_idx]
            if len(bin_data['actual']) > 0:
                predicted_prob = np.mean(bin_data['predicted'])
                actual_freq = np.mean(bin_data['actual'])
                error = abs(predicted_prob - actual_freq)
                calibration_errors.append(error)
        
        if len(calibration_errors) == 0:
            return 0.0
        
        # Mean absolute calibration error
        return np.mean(calibration_errors)
    
    def detect_overfitting(self, train_accuracy, val_accuracy):
        """
        Detect if model is overfitting by comparing train vs validation accuracy
        
        Args:
            train_accuracy: Accuracy on training set
            val_accuracy: Accuracy on validation set
        
        Returns:
            (is_overfitting, gap)
        """
        self.train_accuracy_history.append(train_accuracy)
        self.val_accuracy_history.append(val_accuracy)
        
        if len(self.train_accuracy_history) < 10:
            return False, 0.0
        
        # Calculate average gap
        train_avg = np.mean(self.train_accuracy_history)
        val_avg = np.mean(self.val_accuracy_history)
        
        gap = train_avg - val_avg
        
        # Overfitting if train accuracy is more than 10% higher than validation
        is_overfitting = gap > 0.10
        
        return is_overfitting, gap
    
    def confidence_interval(self, confidence_level=0.95):
        """
        Calculate confidence interval for win ratio
        
        Returns:
            (lower_bound, upper_bound)
        """
        n = len(self.prediction_outcomes)
        
        if n < 10:
            return (0.0, 1.0)
        
        x = sum(self.prediction_outcomes)
        win_ratio = x / n
        
        # Wilson score interval (better for proportions than normal approximation)
        z = stats.norm.ppf((1 + confidence_level) / 2)
        
        denominator = 1 + z**2 / n
        center = (win_ratio + z**2 / (2*n)) / denominator
        margin = z * np.sqrt(win_ratio * (1 - win_ratio) / n + z**2 / (4*n**2)) / denominator
        
        lower = max(0.0, center - margin)
        upper = min(1.0, center + margin)
        
        return (lower, upper)
    
    def get_comprehensive_report(self):
        """
        Generate comprehensive statistical report
        """
        is_significant, p_value, z_score, win_ratio = self.binomial_test()
        sharpe = self.sharpe_ratio()
        ic = self.information_coefficient()
        calib_error = self.calibration_score()
        ci_lower, ci_upper = self.confidence_interval()
        
        n_predictions = len(self.prediction_outcomes)
        
        report = {
            'n_predictions': n_predictions,
            'win_ratio': win_ratio,
            'confidence_interval': (ci_lower, ci_upper),
            'is_statistically_significant': is_significant,
            'p_value': p_value,
            'z_score': z_score,
            'sharpe_ratio': sharpe,
            'information_coefficient': ic,
            'calibration_error': calib_error,
            'passes_significance': is_significant and p_value < 0.05,
            'passes_sharpe': sharpe > 1.0,
            'passes_ic': ic > 0.05,
            'passes_calibration': calib_error < 0.10,
            'overall_confidence': 'HIGH' if (is_significant and sharpe > 1.0 and ic > 0.05) else 
                                 'MEDIUM' if is_significant else 'LOW'
        }
        
        return report
    
    def print_report(self):
        """Print formatted statistical report"""
        report = self.get_comprehensive_report()
        
        print("\n" + "="*80)
        print("STATISTICAL VALIDATION REPORT")
        print("="*80)
        print(f"Total Predictions: {report['n_predictions']}")
        print(f"Win Ratio: {report['win_ratio']:.2%}")
        print(f"95% Confidence Interval: [{report['confidence_interval'][0]:.2%}, {report['confidence_interval'][1]:.2%}]")
        print("-"*80)
        print("Statistical Significance (vs random guessing):")
        print(f"  ✓ Significant: {report['is_statistically_significant']}" if report['passes_significance'] else 
              f"  ✗ Not significant: {report['is_statistically_significant']}")
        print(f"  p-value: {report['p_value']:.4f} (threshold: 0.05)")
        print(f"  z-score: {report['z_score']:.2f}")
        print("-"*80)
        print("Financial Metrics:")
        print(f"  Sharpe Ratio: {report['sharpe_ratio']:.2f} {'✓ (>1.0)' if report['passes_sharpe'] else '✗ (<1.0)'}")
        print(f"  Information Coefficient: {report['information_coefficient']:.3f} {'✓ (>0.05)' if report['passes_ic'] else '✗ (<0.05)'}")
        print(f"  Calibration Error: {report['calibration_error']:.3f} {'✓ (<0.10)' if report['passes_calibration'] else '✗ (>0.10)'}")
        print("-"*80)
        print(f"Overall Confidence: {report['overall_confidence']}")
        print("="*80)
        
        return report
