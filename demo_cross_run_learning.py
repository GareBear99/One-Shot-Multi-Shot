#!/usr/bin/env python3
"""
Demonstration of cross-run learning
Runs the system 3 times consecutively to show accumulated knowledge
"""
import os
import sys
import pandas as pd
import logging
from datetime import datetime
from ml_adaptive_trader import MLAdaptiveBacktest

# Suppress most logs for cleaner output
logging.basicConfig(level=logging.WARNING)

def run_single_test(run_number, initial_balance=10000, num_strategies=5):
    """Run a single backtest and return metrics"""
    print(f"\n{'='*80}")
    print(f"RUN #{run_number}")
    print(f"{'='*80}")
    
    # Load synthetic data
    data_dir = "/Users/TheRustySpoon/Desktop/Projects/Main projects/Trading_bots/One_Shot/minute_data"
    csv_file = os.path.join(data_dir, "synthetic_learnable.csv")
    
    df = pd.read_csv(csv_file, comment='#')
    df['timestamp'] = pd.to_datetime(df['date'])
    df = df[df['interpolated'] == True].copy()
    df = df.dropna(subset=['price'])
    df = df.reset_index(drop=True)
    
    print(f"Data points: {len(df)}")
    
    # Run backtest with model loading enabled
    backtest = MLAdaptiveBacktest(
        initial_balance=initial_balance, 
        num_strategies=num_strategies,
        load_latest_model=True
    )
    
    report = backtest.run_backtest(df, "ETH")
    
    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_file = f"ml_model_{timestamp}.pkl"
    backtest.ml_engine.save_model(model_file)
    
    # Extract metrics
    metrics = {
        'run': run_number,
        'total_predictions': backtest.ml_engine.total_predictions,
        'win_ratio': backtest.ml_engine.real_time_win_ratio,
        'prediction_inversion': backtest.ml_engine.prediction_inversion,
        'confidence_penalty': backtest.ml_engine.confidence_penalty,
        'improvement_segments': len(backtest.ml_engine.improvement_tracker.segments),
        'improvement_trend': backtest.ml_engine.improvement_tracker.improvement_trend,
    }
    
    if report:
        metrics.update({
            'total_return': report['total_return'],
            'profit_factor': report['profit_factor'],
            'total_trades': report['total_trades'],
        })
    
    return metrics

def main():
    print("\n" + "="*80)
    print("CROSS-RUN LEARNING DEMONSTRATION")
    print("="*80)
    print("\nThis will run the system 3 times consecutively.")
    print("Each run should build on the previous run's learning.")
    print("\nExpected behavior:")
    print("  - Total predictions should ACCUMULATE across runs")
    print("  - Win ratio should improve (or at least persist)")
    print("  - Learning state (inversion, penalties) should persist")
    print("  - Improvement segments should continue from previous runs")
    
    input("\nPress ENTER to start (or Ctrl+C to cancel)...")
    
    # Delete old models to start fresh
    import glob
    old_models = glob.glob("ml_model_*.pkl")
    if old_models:
        print(f"\nCleaning up {len(old_models)} old model files...")
        for model in old_models:
            os.remove(model)
        print("✓ Cleanup complete - starting fresh")
    
    # Run 3 consecutive tests
    results = []
    for i in range(1, 4):
        metrics = run_single_test(i, initial_balance=10000, num_strategies=5)
        results.append(metrics)
        
        # Print summary
        print(f"\n{'-'*80}")
        print(f"RUN #{i} SUMMARY:")
        print(f"{'-'*80}")
        print(f"Total Predictions:     {metrics['total_predictions']:,}")
        print(f"Win Ratio:             {metrics['win_ratio']:.2%}")
        print(f"Inversion Active:      {metrics['prediction_inversion']}")
        print(f"Confidence Penalty:    {metrics['confidence_penalty']:.3f}")
        print(f"Improvement Segments:  {metrics['improvement_segments']}")
        print(f"Improvement Trend:     {metrics['improvement_trend']:+.4f}")
        if 'total_return' in metrics:
            print(f"Total Return:          {metrics['total_return']:.2f}%")
            print(f"Profit Factor:         {metrics['profit_factor']:.2f}")
        print(f"{'-'*80}")
        
        if i < 3:
            print("\n⏱  Waiting 2 seconds before next run...")
            import time
            time.sleep(2)
    
    # Final comparison
    print("\n\n" + "="*80)
    print("CROSS-RUN LEARNING RESULTS")
    print("="*80)
    print(f"\n{'Metric':<30} {'Run 1':<15} {'Run 2':<15} {'Run 3':<15}")
    print("-"*80)
    
    # Total predictions
    preds = [r['total_predictions'] for r in results]
    print(f"{'Total Predictions':<30} {preds[0]:<15,} {preds[1]:<15,} {preds[2]:<15,}")
    
    # Win ratio
    wrs = [r['win_ratio'] for r in results]
    print(f"{'Win Ratio':<30} {wrs[0]:<15.2%} {wrs[1]:<15.2%} {wrs[2]:<15.2%}")
    
    # Confidence penalty
    cps = [r['confidence_penalty'] for r in results]
    print(f"{'Confidence Penalty':<30} {cps[0]:<15.3f} {cps[1]:<15.3f} {cps[2]:<15.3f}")
    
    # Improvement segments
    segs = [r['improvement_segments'] for r in results]
    print(f"{'Improvement Segments':<30} {segs[0]:<15} {segs[1]:<15} {segs[2]:<15}")
    
    # Returns
    if all('total_return' in r for r in results):
        rets = [r['total_return'] for r in results]
        print(f"{'Total Return':<30} {rets[0]:<15.2f}% {rets[1]:<15.2f}% {rets[2]:<15.2f}%")
    
    print("="*80)
    
    # Validate learning
    print("\nVALIDATION:")
    
    # Check 1: Predictions accumulate
    if preds[1] > preds[0] and preds[2] > preds[1]:
        print("✓ PASS: Total predictions accumulating across runs")
    else:
        print("✗ FAIL: Predictions not accumulating!")
        print(f"  Run 1: {preds[0]}, Run 2: {preds[1]}, Run 3: {preds[2]}")
    
    # Check 2: Improvement segments accumulate
    if segs[1] >= segs[0] and segs[2] >= segs[1]:
        print("✓ PASS: Improvement segments accumulating")
    else:
        print("✗ FAIL: Improvement segments not accumulating!")
        print(f"  Run 1: {segs[0]}, Run 2: {segs[1]}, Run 3: {segs[2]}")
    
    # Check 3: Model is learning (win ratio improving or stable above 50%)
    if wrs[2] >= 0.50 or wrs[2] > wrs[0]:
        print("✓ PASS: Model showing learning (win ratio ≥50% or improving)")
    else:
        print("⚠ WARNING: Win ratio not improving")
        print(f"  Run 1: {wrs[0]:.2%}, Run 2: {wrs[1]:.2%}, Run 3: {wrs[2]:.2%}")
    
    print("\n" + "="*80)
    if preds[1] > preds[0] and preds[2] > preds[1] and segs[1] >= segs[0]:
        print("✓✓✓ SUCCESS: Model is persisting learning across runs! ✓✓✓")
    else:
        print("✗ Model persistence issue detected")
    print("="*80)

if __name__ == "__main__":
    main()
