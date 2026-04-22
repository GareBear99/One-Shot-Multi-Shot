#!/usr/bin/env python3
"""
Test if ML model improves across multiple runs with persistence
"""
import os
import pandas as pd
from ml_adaptive_trader import MLAdaptiveBacktest, logger

def run_with_persistence(run_number, model_path="persistent_model.pkl"):
    """Run backtest with model persistence"""
    print(f"\n{'='*80}")
    print(f"RUN {run_number}")
    print(f"{'='*80}")
    
    # Load data
    data_dir = "/Users/TheRustySpoon/Desktop/Projects/Main projects/Trading_bots/One_Shot/minute_data"
    csv_file = os.path.join(data_dir, "eth_minute.csv")
    
    df = pd.read_csv(csv_file, comment='#')
    df['timestamp'] = pd.to_datetime(df['date'])
    df = df[df['interpolated'] == True].copy()
    df = df.dropna(subset=['price'])
    df = df.reset_index(drop=True)
    
    # Create backtest with model loading
    backtest = MLAdaptiveBacktest(initial_balance=10000, num_strategies=3)
    
    # Load existing model if available
    if os.path.exists(model_path) and run_number > 1:
        logger.info(f"Loading model from previous run: {model_path}")
        backtest.ml_engine.load_model(model_path)
    
    # Run backtest
    report = backtest.run_backtest(df, f"ETH_Run{run_number}")
    
    # Save model for next run
    backtest.ml_engine.save_model(model_path)
    
    # Extract key metrics
    pred_stats = backtest.ml_engine.get_prediction_stats()
    
    return {
        'run': run_number,
        'win_ratio': pred_stats['win_ratio'],
        'total_predictions': pred_stats['total_predictions'],
        'correct_predictions': pred_stats['correct_predictions'],
        'validated_predictions': pred_stats['validated_predictions']
    }

def main():
    """Run multiple backtests with persistent learning"""
    model_path = "persistent_model.pkl"
    
    # Clean slate
    if os.path.exists(model_path):
        os.remove(model_path)
        print("Removed old model - starting fresh")
    
    results = []
    num_runs = 5
    
    print("\n" + "="*80)
    print("TESTING PERSISTENT LEARNING ACROSS RUNS")
    print("="*80)
    
    for run in range(1, num_runs + 1):
        result = run_with_persistence(run, model_path)
        results.append(result)
        
        print(f"\nRUN {run} SUMMARY:")
        print(f"  Win Ratio: {result['win_ratio']:.2%}")
        print(f"  Total Predictions: {result['total_predictions']}")
        print(f"  Correct: {result['correct_predictions']}")
        print(f"  Validated: {result['validated_predictions']}")
    
    # Summary table
    print("\n" + "="*80)
    print("LEARNING PROGRESSION ACROSS RUNS")
    print("="*80)
    print(f"{'Run':<6} {'Win Ratio':<12} {'Total Pred':<12} {'Correct':<10}")
    print("-"*80)
    
    for r in results:
        print(f"{r['run']:<6} {r['win_ratio']:<12.2%} {r['total_predictions']:<12} {r['correct_predictions']:<10}")
    
    # Check if learning improved
    if len(results) >= 2:
        improvement = results[-1]['win_ratio'] - results[0]['win_ratio']
        print("\n" + "="*80)
        if improvement > 0:
            print(f"✅ MODEL IMPROVED: +{improvement:.2%} from Run 1 to Run {num_runs}")
        elif improvement < 0:
            print(f"❌ MODEL DEGRADED: {improvement:.2%} from Run 1 to Run {num_runs}")
        else:
            print(f"⚠️  NO CHANGE: Win ratio unchanged from Run 1 to Run {num_runs}")
        print("="*80)

if __name__ == "__main__":
    main()
