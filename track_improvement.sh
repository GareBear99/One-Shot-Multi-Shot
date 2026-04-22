#!/bin/bash
# Track improvement across multiple runs

cd "/Users/TheRustySpoon/Desktop/Projects/Main projects/Trading_bots/One_Shot"

# Clean start
rm -f ml_model_*.pkl

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     TRACKING CONTINUOUS IMPROVEMENT ACROSS 3 RUNS             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

for run in 1 2 3; do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                          RUN $run"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Run and extract key metrics
    python ml_adaptive_trader.py <<EOF 2>&1 | tee /tmp/run_output.txt | tail -50
10000
2
EOF
    
    # Extract and display key metrics
    echo ""
    echo "📊 KEY METRICS:"
    grep "Loaded previous" /tmp/run_output.txt | head -1
    grep "Real-Time Win Ratio:" /tmp/run_output.txt | head -1
    grep "Learning Status:" /tmp/run_output.txt | head -1
    grep "Overall Improvement:" /tmp/run_output.txt | head -1
    grep "Total Return:" /tmp/run_output.txt | head -1
    grep "Profit Factor:" /tmp/run_output.txt | head -1
    grep "Recommendation:" /tmp/run_output.txt | head -1
    echo ""
    
    sleep 2
done

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    TRACKING COMPLETE                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
