#!/usr/bin/env python3
"""
Improvement Tracker - Validates system is continuously learning and improving
Monitors win ratio trends to confirm the system is getting better over time
"""
import numpy as np
from collections import deque
import logging

logger = logging.getLogger(__name__)


class ImprovementTracker:
    """
    Tracks system improvement over time
    Validates that learning is actually working by monitoring trends
    """
    
    def __init__(self, window_size=100):
        self.window_size = window_size
        
        # Track win ratio over time (segmented)
        self.segments = []  # Each segment = 100 predictions
        self.current_segment_predictions = []
        
        # Overall metrics
        self.total_predictions = 0
        self.total_correct = 0
        
        # Improvement detection
        self.is_improving = False
        self.improvement_trend = 0.0  # Slope of win ratio over segments
        self.consecutive_improvements = 0
        self.consecutive_degradations = 0
        
    def add_prediction(self, was_correct):
        """Add a prediction outcome"""
        self.total_predictions += 1
        if was_correct:
            self.total_correct += 1
        
        self.current_segment_predictions.append(1 if was_correct else 0)
        
        # Complete segment every window_size predictions
        if len(self.current_segment_predictions) >= self.window_size:
            segment_win_ratio = np.mean(self.current_segment_predictions)
            self.segments.append({
                'segment_num': len(self.segments) + 1,
                'win_ratio': segment_win_ratio,
                'predictions': len(self.current_segment_predictions),
                'correct': sum(self.current_segment_predictions)
            })
            
            # Reset for next segment
            self.current_segment_predictions = []
            
            # Check for improvement after we have enough segments
            if len(self.segments) >= 3:
                self._check_improvement()
    
    def _check_improvement(self):
        """Check if system is improving over time"""
        if len(self.segments) < 3:
            return
        
        # Get last 5 segments (or all if less than 5)
        recent_segments = self.segments[-5:]
        win_ratios = [s['win_ratio'] for s in recent_segments]
        
        # Calculate trend using linear regression
        x = np.arange(len(win_ratios))
        
        if len(win_ratios) >= 2:
            # Linear regression: y = mx + b
            coeffs = np.polyfit(x, win_ratios, 1)
            slope = coeffs[0]  # This is the trend
            self.improvement_trend = slope
            
            # Positive slope = improving
            self.is_improving = slope > 0.01  # At least 1% improvement per segment
            
            # Track consecutive improvements/degradations
            if slope > 0.01:
                self.consecutive_improvements += 1
                self.consecutive_degradations = 0
            elif slope < -0.01:
                self.consecutive_degradations += 1
                self.consecutive_improvements = 0
    
    def get_current_win_ratio(self):
        """Get overall win ratio"""
        if self.total_predictions == 0:
            return 0.5
        return self.total_correct / self.total_predictions
    
    def get_recent_win_ratio(self, n_segments=3):
        """Get win ratio from last N segments"""
        if len(self.segments) < n_segments:
            return self.get_current_win_ratio()
        
        recent = self.segments[-n_segments:]
        total_predictions = sum(s['predictions'] for s in recent)
        total_correct = sum(s['correct'] for s in recent)
        
        if total_predictions == 0:
            return 0.5
        
        return total_correct / total_predictions
    
    def get_improvement_status(self):
        """
        Get detailed improvement status
        
        Returns:
            dict with improvement metrics
        """
        if len(self.segments) < 3:
            return {
                'status': 'INSUFFICIENT_DATA',
                'message': f'Need at least 3 segments (300 predictions). Currently: {len(self.segments)} segments',
                'is_improving': False,
                'trend': 0.0
            }
        
        # Calculate statistics
        first_3_win_ratio = np.mean([s['win_ratio'] for s in self.segments[:3]])
        last_3_win_ratio = self.get_recent_win_ratio(3)
        overall_improvement = last_3_win_ratio - first_3_win_ratio
        
        # Determine status
        if self.is_improving:
            if last_3_win_ratio > 0.55:
                status = 'EXCELLENT'
                message = f'System is improving! Win ratio: {last_3_win_ratio:.2%} (trend: +{self.improvement_trend:.3f}/segment)'
            elif last_3_win_ratio > 0.50:
                status = 'GOOD'
                message = f'System is learning and improving. Win ratio: {last_3_win_ratio:.2%}'
            else:
                status = 'IMPROVING_BUT_WEAK'
                message = f'System improving but still below 50%. Win ratio: {last_3_win_ratio:.2%}'
        else:
            if last_3_win_ratio > 0.50:
                status = 'STABLE'
                message = f'System is stable above 50%. Win ratio: {last_3_win_ratio:.2%}'
            elif self.improvement_trend < -0.01:
                status = 'DEGRADING'
                message = f'⚠️  System is degrading! Win ratio: {last_3_win_ratio:.2%} (trend: {self.improvement_trend:.3f}/segment)'
            else:
                status = 'FLAT'
                message = f'System not learning patterns. Win ratio: {last_3_win_ratio:.2%} (flat data?)'
        
        return {
            'status': status,
            'message': message,
            'is_improving': self.is_improving,
            'trend': self.improvement_trend,
            'current_win_ratio': self.get_current_win_ratio(),
            'recent_win_ratio': last_3_win_ratio,
            'first_3_segments': first_3_win_ratio,
            'improvement_delta': overall_improvement,
            'consecutive_improvements': self.consecutive_improvements,
            'consecutive_degradations': self.consecutive_degradations,
            'total_segments': len(self.segments),
            'total_predictions': self.total_predictions
        }
    
    def should_continue_trading(self):
        """
        Determine if system should continue trading
        
        Returns:
            (should_continue, reason)
        """
        status = self.get_improvement_status()
        
        # Not enough data yet
        if status['status'] == 'INSUFFICIENT_DATA':
            return True, "Collecting data"
        
        # System is degrading for too long - STOP
        if status['status'] == 'DEGRADING' and self.consecutive_degradations >= 3:
            return False, "System has been degrading for 3+ segments - STOP TRADING"
        
        # Win ratio too low for too long - STOP
        if len(self.segments) >= 10 and status['recent_win_ratio'] < 0.45:
            return False, "Win ratio below 45% after 1000+ predictions - STOP TRADING"
        
        # System working well - CONTINUE
        if status['status'] in ['EXCELLENT', 'GOOD', 'STABLE']:
            return True, f"System validated: {status['message']}"
        
        # System improving but need more data - CONTINUE
        if status['is_improving']:
            return True, "System is improving - continue learning"
        
        # Flat data (like our test data) - CONTINUE but with caution
        if status['status'] == 'FLAT':
            return True, "No patterns detected - may be flat/test data"
        
        # Default: continue
        return True, "Monitoring system performance"
    
    def print_improvement_report(self):
        """Print detailed improvement report"""
        status = self.get_improvement_status()
        
        print("\n" + "="*80)
        print("CONTINUOUS IMPROVEMENT VALIDATION")
        print("="*80)
        print(f"Status: {status['status']}")
        print(f"Message: {status['message']}")
        print("-"*80)
        print(f"Total Predictions: {status['total_predictions']}")
        print(f"Total Segments: {status['total_segments']} (each = {self.window_size} predictions)")
        print(f"Overall Win Ratio: {status['current_win_ratio']:.2%}")
        print(f"Recent Win Ratio (last 3 segments): {status['recent_win_ratio']:.2%}")
        print("-"*80)
        print(f"Improvement Trend: {status['trend']:.4f} per segment")
        print(f"First 3 Segments Avg: {status['first_3_segments']:.2%}")
        print(f"Improvement Delta: {status['improvement_delta']:+.2%}")
        print(f"Is Improving: {'YES ✓' if status['is_improving'] else 'NO ✗'}")
        print("-"*80)
        
        # Show segment history
        if len(self.segments) > 0:
            print("Segment History (last 10):")
            recent_segments = self.segments[-10:]
            for seg in recent_segments:
                print(f"  Segment {seg['segment_num']:3d}: {seg['win_ratio']:.2%} ({seg['correct']}/{seg['predictions']})")
        
        print("="*80)
        
        # Should continue trading?
        should_continue, reason = self.should_continue_trading()
        if should_continue:
            print(f"✓ CONTINUE TRADING: {reason}")
        else:
            print(f"✗ STOP TRADING: {reason}")
        print("="*80)
        
        return status
