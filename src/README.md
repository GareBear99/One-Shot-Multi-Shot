# OneShot Live ML System

**Status:** ✅ Ready for testing  
**Created:** 2026-01-07  
**Components:** 4 modules + test interface

---

## 🎯 What This Does

Connects OneShot to **live Bitcoin price data** via Binance WebSocket and makes **real predictions** using machine learning that **adapts** based on performance.

### Key Features:
- ✅ **Real-time market data** from Binance (public, no auth needed)
- ✅ **10 predictive features** (momentum, volatility, trend, etc.)
- ✅ **Adaptive ML model** (logistic regression with online learning)
- ✅ **Gets more aggressive when losing** (increases learning rate)
- ✅ **Adjusts confidence threshold** dynamically
- ✅ **Paper trading** to validate predictions
- ✅ **Model persistence** (save/load from localStorage)

---

## 📁 File Structure

```
src/
├── market_feed.js         # Binance WebSocket connection
├── feature_extractor.js   # Extract features from prices
├── ml_model.js           # Adaptive logistic regression
├── oneshot_live.js       # Main integration
└── README.md            # This file

test_live_ml.html         # Test interface (open in browser)
```

---

## 🚀 Quick Start

### 1. Open Test Interface
```bash
# Just open in your browser:
open test_live_ml.html

# Or navigate to:
file:///Users/TheRustySpoon/Desktop/Projects/Main%20projects/Trading_bots/One_Shot/test_live_ml.html
```

### 2. Press START
- Wait 5-10 seconds for data to buffer
- Predictions start streaming every 1 second
- Paper trades resolve after 30 seconds
- Model learns from every outcome

### 3. Monitor Performance
Watch these metrics:
- **Paper Win Rate** - Should trend toward 60-65%+ over 100+ trades
- **Model WR (last 50)** - Short-term accuracy
- **Aggression Level** - Increases when losing (up to 3.0x)
- **Confidence Threshold** - Dynamically adjusts (65-85%)

---

## 📊 How It Works

### 1. Market Data (market_feed.js)
```javascript
const feed = new MarketFeed('btcusdt');
// Connects to: wss://stream.binance.com:9443/ws/btcusdt@trade
// Buffers last 1000 price ticks
// Auto-reconnects if disconnected
```

### 2. Feature Extraction (feature_extractor.js)
```javascript
const extractor = new FeatureExtractor(prices);
const features = extractor.extractAll();
// Returns: {
//   momentum_1s, momentum_5s, momentum_10s, momentum_30s,
//   volatility_normalized, trend, trend_strength,
//   acceleration, relative_strength, price_position
// }
```

### 3. ML Prediction (ml_model.js)
```javascript
const model = new OneShotModel(10); // 10 features
const prediction = model.predict(features);
// Returns: {
//   direction: 'UP' or 'DOWN',
//   confidence: 0-1,
//   raw_probability: 0-1
// }
```

### 4. Adaptive Learning
```javascript
// After 30 seconds, compare prediction vs actual
const actualDirection = exitPrice > entryPrice ? 'UP' : 'DOWN';
const actualOutcome = actualDirection === 'UP' ? 1 : 0;

// Model learns from mistake/success
model.update(features, actualOutcome);

// If losing, increase aggression
if (winRate < 0.55) {
  aggression *= 1.05; // Learn faster
}

// If losing, be more selective
if (winRate < 0.60) {
  confidenceThreshold += 0.001; // Raise bar
}
```

---

## 🎚️ Adaptive Parameters

### Aggression (Learning Rate Multiplier)
- **Starts at:** 1.0x
- **Increases when:** Win rate < 55%
- **Max:** 3.0x
- **Effect:** Model learns faster when struggling

### Confidence Threshold
- **Starts at:** 75%
- **Range:** 65-85%
- **Increases when:** Losing (be more selective)
- **Decreases when:** Winning (trade more)

---

## 🧪 Testing Checklist

### Phase 1: Connection (5 minutes)
- [ ] Open test_live_ml.html
- [ ] Wait for "✅ Connected"
- [ ] See BTC price updating
- [ ] Total predictions incrementing

### Phase 2: Predictions (30 minutes)
- [ ] Predictions streaming every second
- [ ] Direction: UP/DOWN
- [ ] Confidence: 0-100%
- [ ] Some predictions marked TRADE, others SKIP

### Phase 3: Paper Trading (2 hours)
- [ ] Paper trades resolving after 30 seconds
- [ ] Wins and losses being logged
- [ ] Win rate being calculated
- [ ] Model WR trending upward

### Phase 4: Adaptation (4-8 hours)
- [ ] Aggression increases when losing
- [ ] Threshold adjusts dynamically
- [ ] Win rate stabilizes at 55-65%+
- [ ] Model learning from outcomes

---

## 📈 Expected Performance

### First Hour:
- **Win Rate:** 45-55% (random, model learning)
- **Aggression:** 1.0x → 1.5x
- **Threshold:** 75% → 78%

### After 100 Trades:
- **Win Rate:** 55-60% (model starting to learn patterns)
- **Aggression:** 1.2-1.8x
- **Threshold:** 70-80%

### After 500 Trades:
- **Win Rate:** 58-65% (model should find edges)
- **Aggression:** 1.0-1.5x
- **Threshold:** 68-77%

### After 1000 Trades:
- **Win Rate:** 60-70% (proven or disproven)
- **Aggression:** Stable
- **Threshold:** Stable

**If WR stays below 55% after 500 trades → Model isn't finding edge**

---

## 💾 Model Persistence

### Save Model
```javascript
system.saveModel();
// Saves to localStorage: weights, bias, threshold, aggression
```

### Load Model
```javascript
system.loadModel();
// Loads previous training session
```

**Use Case:** Train for 8 hours, save, resume later without relearning.

---

## 🔧 Integration with Main OneShot

To integrate into the main OneShot HTML:

1. **Include modules in <head>:**
```html
<script src="src/market_feed.js"></script>
<script src="src/feature_extractor.js"></script>
<script src="src/ml_model.js"></script>
<script src="src/oneshot_live.js"></script>
```

2. **Replace fake streamPrediction():**
```javascript
// OLD (fake):
function streamPrediction() {
  const dir = (Math.random() < 0.5) ? "UP" : "DOWN"; // RANDOM!
  // ...
}

// NEW (real):
const liveSystem = new OneShotLive('btcusdt');
liveSystem.start();
liveSystem.onPrediction = (pred) => {
  state.predStream = {
    t: tNow(),
    dir: pred.direction,
    conf: pred.confidence,
    cls: tradeClass(pred.confidence)
  };
  // ... rest of OneShot logic
};
```

3. **Use real outcomes to train:**
```javascript
liveSystem.onTradeResolved = (trade) => {
  // Model already updated internally
  // Just update OneShot UI
  const win = trade.win;
  // ... update state, charts, etc.
};
```

---

## ⚠️ Important Notes

### This is NOT production-ready for real money:
- ❌ **No trade execution** (paper trading only)
- ❌ **Binary options illegal** in many countries
- ❌ **60-65% WR not guaranteed** (market conditions vary)
- ❌ **30-second timeframe** is very short (high variance)

### This IS ready for:
- ✅ **Paper trading validation** (prove concept works)
- ✅ **ML model testing** (see if edge exists)
- ✅ **Feature engineering** (which features matter)
- ✅ **Adaptive learning** (test aggression system)

---

## 🐛 Troubleshooting

### "Connection stuck on ⏳ Connecting..."
- Check internet connection
- Binance WebSocket might be blocked
- Try: `wss://stream.binance.us:9443/ws/btcusdt@trade` (US)

### "No predictions streaming"
- Wait 10-15 seconds for data buffer
- Check browser console for errors
- Try refreshing page

### "Win rate stuck at 50%"
- Expected for first 50-100 trades
- Model needs time to learn
- If still 50% after 500 trades, features may not be predictive

### "Aggression going to 3.0x"
- Model is struggling to find edge
- Normal if WR < 55% sustained
- May indicate no predictable pattern exists

---

## 📊 Monitoring in Console

```javascript
// Get full stats
system.getStats();

// Check model status
system.model.getStatus();

// Get recent predictions
system.getRecentPredictions(50);

// Market feed status
system.marketFeed.getStatus();
```

---

## 🎯 Success Criteria

### Minimum (Proof of Concept):
- [ ] 500+ paper trades
- [ ] Win rate > 55% (better than break-even)
- [ ] Model learns (WR improves over time)

### Target (Production Ready):
- [ ] 1000+ paper trades
- [ ] Win rate 60-65%+ sustained
- [ ] Confidence correlates with accuracy
- [ ] No major bugs or crashes

### Ideal (Profitable):
- [ ] 2000+ paper trades
- [ ] Win rate 65-72%
- [ ] Stable over multiple days
- [ ] All safety systems tested

---

## 🚀 Next Steps

1. **Test for 24 hours** - Let it run, monitor WR
2. **If WR > 60%** - Continue to 1000 trades
3. **If WR > 65%** - Consider real execution integration
4. **If WR < 55%** - Improve features or abandon

**Reality Check:** Most prediction systems fail to beat 55%. If this achieves 60-65%+ sustained, it's exceptional.

---

## 📞 Quick Reference

**Start system:**
```javascript
system.start();
```

**Stop system:**
```javascript
system.stop();
```

**Get stats:**
```javascript
console.log(system.getStats());
```

**Save progress:**
```javascript
system.saveModel();
```

---

**Status:** Ready for 24-hour test  
**Expected First Result:** 2026-01-08 (tomorrow)  
**Target:** 60%+ WR over 500+ trades
