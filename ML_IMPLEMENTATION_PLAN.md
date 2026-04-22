# OneShot Live Trading + ML Implementation Plan
**Target:** 72% Win Rate with Real Market Data + Adaptive ML  
**Status:** Planning Phase  
**Validation Complete:** ✅ 40/40 tests passed

---

## Executive Summary

This plan outlines the path from current **validated demo system** (100% test pass rate) to **live 72% win rate trading** with real market data and adaptive ML. Timeline: 12-22 days full implementation, or **1 day for minimal MVP**.

### Key Success Factors:
1. **Feature Quality > Model Complexity** - Start simple, iterate
2. **Confidence Calibration** - Raw scores ≠ true probability
3. **Smart Trade Selection** - Only trade best setups
4. **Online Learning** - Adapt to market conditions
5. **Hearts System Discipline** - $15/day max loss enforced

---

## Quick Start (1-Day MVP)

### Goal: Live market data with simple momentum model

**Step 1: Binance WebSocket (30 min)**
```javascript
const ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@trade');
let lastPrice = null;
let priceHistory = [];

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  const price = parseFloat(data.p);
  priceHistory.push(price);
  if (priceHistory.length > 100) priceHistory.shift();
  lastPrice = price;
};
```

**Step 2: Simple Momentum Predictor (30 min)**
```javascript
function predictDirection() {
  if (priceHistory.length < 10) return { direction: 'UP', confidence: 0.5 };
  
  const recent5 = priceHistory.slice(-5);
  const prev5 = priceHistory.slice(-10, -5);
  
  const recentAvg = recent5.reduce((a,b) => a+b) / recent5.length;
  const prevAvg = prev5.reduce((a,b) => a+b) / prev5.length;
  
  const momentum = (recentAvg - prevAvg) / prevAvg;
  const direction = momentum > 0 ? 'UP' : 'DOWN';
  const confidence = Math.min(0.9, 0.5 + Math.abs(momentum) * 100);
  
  return { direction, confidence };
}
```

**Step 3: Replace Demo streamPrediction() (15 min)**
```javascript
function streamPrediction() {
  if (!state.running || !gatedAuto()) return;
  
  const pred = predictDirection();
  
  state.predStream = {
    t: tNow(),
    dir: pred.direction,
    conf: pred.confidence,
    cls: tradeClass(pred.confidence)
  };
  
  state.pred[pred.direction] += 1;
  render();
}
```

**Step 4: Track Actual Outcomes (15 min)**
```javascript
const pendingTrades = [];

function executeTrade() {
  // ... existing logic ...
  
  const tradeId = Date.now();
  const entryPrice = lastPrice;
  const direction = state.predStream.dir;
  
  pendingTrades.push({ 
    tradeId, 
    entryPrice, 
    direction, 
    timestamp: Date.now(),
    features: getCurrentFeatures()
  });
  
  // Resolve after 30 seconds
  setTimeout(() => resolveTrade(tradeId), 30000);
}

function resolveTrade(tradeId) {
  const trade = pendingTrades.find(t => t.tradeId === tradeId);
  if (!trade) return;
  
  const exitPrice = lastPrice;
  const actualDirection = exitPrice > trade.entryPrice ? 'UP' : 'DOWN';
  const win = actualDirection === trade.direction;
  
  // Update state and UI with actual result
  // ... rest of logic ...
}
```

**Result:** Live predictions with real BTC price data in ~90 minutes

---

## Phase-by-Phase Implementation

### Phase 1: Live Market Data Integration
**Timeline:** 1-2 days  
**Risk:** Low (read-only)  
**Goal:** Replace demo data with real-time Binance WebSocket

**Deliverables:**
- `MarketFeed` class with WebSocket connection
- Price history buffer (last 1000 ticks)
- Feature extraction (momentum, volatility, micro-trend)
- Integration with existing `streamPrediction()`

**Validation Checklist:**
- [ ] WebSocket connects successfully
- [ ] Prices update every ~100ms
- [ ] Features extract correctly
- [ ] No data gaps > 2 seconds

---

### Phase 2: Lightweight ML Model (Simple)
**Timeline:** 2-3 days  
**Risk:** Medium  
**Goal:** 60-65% win rate with logistic regression

**Core Features (12 total):**
1. Price momentum (1s, 5s, 10s, 30s)
2. Volatility (10s, 30s rolling std)
3. Micro-trend (linear regression slope)
4. Price acceleration (2nd derivative)
5. Volume indicators (if available)
6. Time-of-day (cyclical encoding)
7. Recent win/loss pattern (last 5 trades)
8. Confidence calibration (historical accuracy)

**Model: Logistic Regression**
- Fast training (< 1 second)
- Interpretable weights
- Online learning friendly
- Baseline: 58-62% WR expected

**Validation Checklist:**
- [ ] Model initializes without errors
- [ ] Predictions generated every second
- [ ] Confidence scores in range (0-1)
- [ ] Online learning updates weights
- [ ] Accuracy tracked in history

---

### Phase 3: Enhanced ML Model (Advanced)
**Timeline:** 3-5 days  
**Risk:** High  
**Goal:** 72% win rate with LSTM/Attention

**Model Architecture: Lightweight LSTM**
- Input: Last 60 price points (1-second intervals)
- LSTM layer: 32 units
- Dense layer: 16 units (ReLU)
- Output: 2 units (softmax) → UP/DOWN probabilities
- Total params: ~8K (fast inference < 50ms)

**Training Strategy:**
- Continuous online learning
- Replay buffer (10,000 samples)
- Batch size: 32
- Retrain every 100 samples
- Weight profitable predictions higher

**Confidence Calibration:**
- 20 bins (0-5%, 5-10%, ..., 95-100%)
- Track empirical accuracy in each bin
- Use bin accuracy as calibrated confidence
- Only trade when calibrated conf > 75%

**Validation Checklist:**
- [ ] LSTM trains without errors
- [ ] Inference time < 50ms
- [ ] Calibration bins populated
- [ ] WR ≥ 65% over 1000+ predictions

---

### Phase 4: Smart Trade Gating
**Timeline:** 1-2 days  
**Risk:** Low  
**Goal:** Only trade when edge is strongest

**Enhanced Gates:**
```javascript
function shouldTrade(predStream, state) {
  // Base confidence threshold
  if (predStream.conf < 0.75) return false;
  
  // Rolling accuracy windows
  const wr10 = calcWR(state.outcomes.slice(-10));
  const wr20 = calcWR(state.outcomes.slice(-20));
  const wr50 = calcWR(state.outcomes.slice(-50));
  
  if (wr10 < 0.70) return false;
  if (wr20 < 0.68) return false;
  if (wr50 < 0.60) return false; // NEW
  
  // Loss streak protection
  if (state.streak <= -3) return false;
  
  // Confidence-accuracy correlation
  const confBin = Math.floor(predStream.conf * 10);
  const binAccuracy = state.confCalibration[confBin];
  if (binAccuracy && binAccuracy < 0.65) return false;
  
  // Volatility filter
  const recentVolatility = calcVolatility(state.priceHistory.slice(-30));
  if (recentVolatility > state.volatilityThreshold) return false;
  
  // Mean reversion (override)
  if (state.streak <= -5) return true;
  
  return true;
}
```

**Adaptive Thresholds:**
- Start at 75% confidence threshold
- Increase if WR < 70% (more selective)
- Decrease if WR > 74% and trades < 200/day (more aggressive)
- Adjustment rate: 0.001 per update

---

### Phase 5: Validation & Tuning
**Timeline:** 3-7 days  
**Risk:** Medium  
**Goal:** Verify 72% WR in paper trading

**Paper Trading Mode:**
- Track all predictions
- Don't execute real trades
- Resolve after 30 seconds with actual price
- Log all features, predictions, outcomes

**Performance Metrics Dashboard:**
- Overall WR (all-time, daily, hourly)
- WR by confidence bin (70-75%, 75-80%, 80%+)
- WR by time of day
- WR by P vs S class
- Avg confidence on wins vs losses
- Trade frequency (actual vs target)
- Sharpe ratio
- Max drawdown
- Profit factor

**Tuning Checklist:**
- [ ] Paper trade 1000+ predictions
- [ ] WR ≥ 60% with simple model
- [ ] WR ≥ 72% with enhanced model
- [ ] WR stable across time periods
- [ ] Trade frequency 200+ trades/day
- [ ] Confidence calibration accurate
- [ ] Hearts system works under volatility
- [ ] Max loss stays at $15/day

---

### Phase 6: Real Trade Execution (Production)
**Timeline:** 2-3 days  
**Risk:** HIGH (real money)  
**Goal:** Execute actual trades via API

**Options:**
1. **Pocket Option API** (if available)
2. **IQ Option API** (reverse-engineered, risky)
3. **DeFi Binary Options** (Thales Protocol - RECOMMENDED)
4. **Custom settlement contract**

**Recommended: Thales Protocol on Optimism**
- Decentralized, transparent
- Smart contract settlement
- No KYC required
- 30-60 second options available

**Safety Checks:**
```javascript
class ExecutionSafety {
  constructor() {
    this.dailyLossLimit = 15;
    this.dailyLoss = 0;
    this.minBalance = 15;
  }
  
  canExecute(stake, balance) {
    // Reset daily counter at midnight
    if (Date.now() - this.lastResetTime > 24 * 60 * 60 * 1000) {
      this.dailyLoss = 0;
      this.lastResetTime = Date.now();
    }
    
    // Check daily loss limit
    if (this.dailyLoss >= this.dailyLossLimit) return false;
    
    // Check minimum balance
    if (balance < this.minBalance) return false;
    
    // Check stake validity
    if (stake <= 0 || stake > 20) return false;
    
    return true;
  }
}
```

---

## Critical Success Factors for 72% WR

### 1. Feature Quality > Model Complexity ⭐⭐⭐⭐⭐
**HIGHEST PRIORITY**

- Good features + simple model > Complex model + poor features
- Focus on micro-price patterns (1-30 seconds)
- Incorporate recent win/loss feedback loop
- Time-of-day patterns (crypto volatility during overlaps)

### 2. Confidence Calibration ⭐⭐⭐⭐
**HIGH PRIORITY**

- Raw model outputs ≠ true probability
- Calibrate using historical accuracy in bins
- Only trade when calibrated confidence > 75%

### 3. Smart Trade Selection ⭐⭐⭐⭐
**HIGH PRIORITY**

- Don't trade every prediction
- Wait for high-confidence + favorable recent WR
- Avoid high volatility (whipsaws)
- Mean reversion on extended loss streaks

### 4. Online Learning ⭐⭐⭐
**MEDIUM PRIORITY**

- Model must adapt to changing markets
- Retrain every 100-500 samples
- Replay buffer prevents catastrophic forgetting
- Weight recent samples more heavily

### 5. Hearts System Discipline ⭐⭐⭐
**MEDIUM PRIORITY**

- Enforces $15/day max loss
- Prevents revenge trading
- Natural circuit breaker

---

## Risk Mitigation

### Technical Risks
1. **WebSocket disconnects** → Auto-reconnect with exponential backoff
2. **Model overfitting** → Validation set, monitor train vs val accuracy
3. **Latency issues** → Edge deployment, target < 50ms inference

### Market Risks
1. **Regime change** → Auto-disable if WR < 55% for 50+ trades
2. **Flash crashes** → Volatility filter, pause on extreme moves
3. **Execution slippage** → Account for 1-2% in backtests

### Operational Risks
1. **System downtime** → Cloud hosting, monitoring, auto-restart
2. **API rate limits** → Multiple keys, request queuing
3. **Capital depletion** → Hearts system caps at $15/day

---

## Success Metrics

### Phase 1-2 (Simple Model)
- [ ] Live predictions every 1 second
- [ ] WR ≥ 58% over 500+ predictions
- [ ] Confidence correlates with accuracy
- [ ] System stable for 24+ hours

### Phase 3-4 (Enhanced Model)
- [ ] WR ≥ 65% over 1000+ predictions
- [ ] WR ≥ 72% for P-class (conf > 78%)
- [ ] Trade frequency 150-256/day
- [ ] Max daily loss ≤ $15

### Phase 5-6 (Production)
- [ ] WR ≥ 72% sustained for 7+ days
- [ ] Monthly earnings match projections (±20%)
- [ ] Zero system crashes
- [ ] All safety checks functioning

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 | 1-2 days | Live market data |
| Phase 2 | 2-3 days | Simple ML (60-65% WR) |
| Phase 3 | 3-5 days | Enhanced ML (72% WR) |
| Phase 4 | 1-2 days | Smart gating |
| Phase 5 | 3-7 days | Paper trading validation |
| Phase 6 | 2-3 days | Real execution |

**Total: 12-22 days** (optimistic to conservative)  
**Quick MVP: 1 day** (minimal version)

---

## Next Immediate Actions

### TODAY:
1. Set up Binance WebSocket in HTML
2. Implement simple momentum predictions
3. Track actual outcomes vs predictions

### TOMORROW:
4. Add feature extraction (momentum, volatility, trend)
5. Implement logistic regression model

### DAY 3:
6. Test for 24 hours, measure WR
7. Tune thresholds and gates

### DAY 4-5:
8. Optimize to 65%+ WR
9. Add confidence calibration

### WEEK 2:
10. Implement LSTM if needed for 72%
11. Paper trade for 1000+ predictions

---

## File Structure (Planned)

```
One_Shot/
├── README.md
├── VALIDATION_REPORT.md
├── QUICK_REFERENCE.md
├── ML_IMPLEMENTATION_PLAN.md (this file)
├── validate_system.js
├── Docs/
│   └── OneShot_Layman_Guide_v8_LiveGUI_TRUEStreaming_Fixes.html
└── src/ (NEW)
    ├── data/
    │   └── market_feed.js
    ├── ml/
    │   ├── features.js
    │   ├── model_simple.js
    │   ├── model_lstm.js
    │   ├── trainer.js
    │   └── calibration.js
    ├── strategy/
    │   └── adaptive_gates.js
    └── execution/
        ├── thales_executor.js
        └── safety.js
```

---

## Conclusion

The system is **fully validated** (40/40 tests passed) and ready for ML integration. The infrastructure is sound, the math is correct, and the path to 72% WR is clear:

1. **Start simple** - Momentum model first
2. **Measure everything** - Track WR, confidence, features
3. **Iterate quickly** - 1-day cycles, test and tune
4. **Calibrate carefully** - Raw confidence ≠ accuracy
5. **Gate intelligently** - Only trade best setups

**Avoid over-engineering.** Get live data flowing first, then add ML incrementally. The hearts system protects downside while we optimize for 72% WR.

---

**Status:** ✅ Planning Complete  
**Next Step:** Implement Phase 1 (Live Market Data)  
**Timeline:** Start today, MVP in 1 day, full system in 12-22 days
