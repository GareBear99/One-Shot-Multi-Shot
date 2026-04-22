#!/usr/bin/env python3
"""
Test script to verify model persistence is working correctly
"""
import pickle
import os
from ml_adaptive_trader import OnlineLearningEngine

def test_load_latest_model():
    """Test loading the latest model file"""
    print("=" * 80)
    print("TESTING MODEL PERSISTENCE FIX")
    print("=" * 80)
    
    # Find the latest model
    import glob
    model_files = glob.glob("ml_model_*.pkl")
    
    if not model_files:
        print("✗ No model files found!")
        return False
    
    latest_model = max(model_files, key=lambda x: os.path.getmtime(x))
    print(f"\nFound latest model: {latest_model}")
    
    # Try to load it
    print("\nAttempting to load model...")
    engine = OnlineLearningEngine()
    
    try:
        engine.load_model(latest_model)
        print("✓ Model loaded successfully!")
        
        # Check what state was loaded
        print("\n" + "-" * 80)
        print("LOADED STATE:")
        print("-" * 80)
        print(f"Total Predictions:         {engine.total_predictions}")
        print(f"Correct Predictions:       {engine.correct_predictions}")
        print(f"Win Ratio:                 {engine.real_time_win_ratio:.2%}")
        print(f"Recent Accuracy:           {engine.recent_accuracy:.2%}")
        print(f"Consecutive Losses:        {engine.consecutive_losses}")
        print(f"Consecutive Wins:          {engine.consecutive_wins}")
        print(f"Confidence Penalty:        {engine.confidence_penalty:.3f}")
        print(f"Prediction Inversion:      {engine.prediction_inversion}")
        print(f"Inversion Check Count:     {engine.inversion_check_count}")
        print(f"Validated Predictions:     {len(engine.validated_predictions)}")
        print(f"Improvement Segments:      {len(engine.improvement_tracker.segments)}")
        print(f"Improvement Trend:         {engine.improvement_tracker.improvement_trend:+.4f}")
        print("-" * 80)
        
        if engine.total_predictions > 0:
            print("\n✓ SUCCESS: Model has accumulated learning state!")
            print("  The model is persisting data between runs.")
            return True
        else:
            print("\n✗ WARNING: Model loaded but has no predictions!")
            print("  This might be a fresh model.")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR loading model: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_save_and_load():
    """Test saving and loading a model with mock state"""
    print("\n\n" + "=" * 80)
    print("TESTING SAVE/LOAD ROUNDTRIP")
    print("=" * 80)
    
    # Create a fresh engine
    engine1 = OnlineLearningEngine()
    
    # Set some state
    engine1.total_predictions = 12345
    engine1.correct_predictions = 7000
    engine1.real_time_win_ratio = 0.567
    engine1.prediction_inversion = True
    engine1.inversion_check_count = 42
    engine1.confidence_penalty = 0.75
    engine1.consecutive_losses = 3
    
    print("\nOriginal state:")
    print(f"  Total predictions: {engine1.total_predictions}")
    print(f"  Win ratio: {engine1.real_time_win_ratio:.2%}")
    print(f"  Inversion: {engine1.prediction_inversion}")
    print(f"  Confidence penalty: {engine1.confidence_penalty}")
    
    # Save it
    test_file = "test_model_persistence.pkl"
    try:
        engine1.save_model(test_file)
        print(f"\n✓ Model saved to {test_file}")
        
        # Load into new engine
        engine2 = OnlineLearningEngine()
        engine2.load_model(test_file)
        
        print("\nLoaded state:")
        print(f"  Total predictions: {engine2.total_predictions}")
        print(f"  Win ratio: {engine2.real_time_win_ratio:.2%}")
        print(f"  Inversion: {engine2.prediction_inversion}")
        print(f"  Confidence penalty: {engine2.confidence_penalty}")
        
        # Verify
        success = True
        if engine2.total_predictions != engine1.total_predictions:
            print("✗ Total predictions mismatch!")
            success = False
        if engine2.real_time_win_ratio != engine1.real_time_win_ratio:
            print("✗ Win ratio mismatch!")
            success = False
        if engine2.prediction_inversion != engine1.prediction_inversion:
            print("✗ Inversion flag mismatch!")
            success = False
        if engine2.confidence_penalty != engine1.confidence_penalty:
            print("✗ Confidence penalty mismatch!")
            success = False
        if engine2.consecutive_losses != engine1.consecutive_losses:
            print("✗ Consecutive losses mismatch!")
            success = False
            
        if success:
            print("\n✓ SUCCESS: All state variables persisted correctly!")
        
        # Cleanup
        os.remove(test_file)
        return success
        
    except Exception as e:
        print(f"\n✗ ERROR in save/load test: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(test_file):
            os.remove(test_file)
        return False

if __name__ == "__main__":
    test1 = test_load_latest_model()
    test2 = test_save_and_load()
    
    print("\n\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Load latest model test:  {'✓ PASS' if test1 else '✗ FAIL'}")
    print(f"Save/load roundtrip:     {'✓ PASS' if test2 else '✗ FAIL'}")
    print("=" * 80)
    
    if test1 and test2:
        print("\n✓✓✓ ALL TESTS PASSED - Model persistence is working! ✓✓✓")
    else:
        print("\n✗ SOME TESTS FAILED - Model persistence needs investigation")
