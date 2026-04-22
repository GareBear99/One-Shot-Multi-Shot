/**
 * OneShot Live Trading System
 * Complete integration: MarketFeed + Features + ML + Paper Trading
 */

class OneShotLive {
  constructor(symbol = 'btcusdt') {
    // Initialize components
    this.marketFeed = new MarketFeed(symbol);
    this.model = new OneShotModel(10); // 10 features
    this.paperTrades = [];
    this.isRunning = false;
    this.isPaperTrading = true; // Start in paper trading mode
    
    // Prediction tracking
    this.predictionHistory = [];
    this.maxPredictionHistory = 1000;
    
    // Timers
    this.predictionInterval = null;
    this.validationInterval = null;
    this.batchTrainInterval = null;
    
    // Callbacks for UI updates
    this.onPrediction = null;
    this.onTradeResolved = null;
    this.onStatusUpdate = null;
    
    // Stats
    this.stats = {
      totalPredictions: 0,
      totalTrades: 0,
      paperWins: 0,
      paperLosses: 0,
      startTime: null
    };
    
    // Setup market feed listener
    this.setupMarketFeed();
  }
  
  /**
   * Setup market feed listener
   */
  setupMarketFeed() {
    this.marketFeed.subscribe((data) => {
      if (data.type === 'connected') {
        console.log('[OneShotLive] ✅ Market feed connected');
        this.notifyStatus({ connected: true });
      } else if (data.type === 'disconnected') {
        console.log('[OneShotLive] ⚠️ Market feed disconnected');
        this.notifyStatus({ connected: false });
      } else if (data.type === 'error') {
        console.error('[OneShotLive] ❌ Market feed error:', data.message);
      }
    });
  }
  
  /**
   * Start prediction engine
   */
  start() {
    if (this.isRunning) {
      console.warn('[OneShotLive] Already running');
      return;
    }
    
    if (!this.marketFeed.hasEnoughData(50)) {
      console.warn('[OneShotLive] Not enough market data yet. Waiting...');
      setTimeout(() => this.start(), 5000);
      return;
    }
    
    console.log('[OneShotLive] 🚀 Starting prediction engine...');
    this.isRunning = true;
    this.stats.startTime = Date.now();
    
    // Make predictions every 1 second
    this.predictionInterval = setInterval(() => {
      this.makePrediction();
    }, 1000);
    
    // Validate paper trades every 5 seconds
    this.validationInterval = setInterval(() => {
      this.validatePaperTrades();
    }, 5000);
    
    // Batch train every 30 seconds (if enough data)
    this.batchTrainInterval = setInterval(() => {
      if (this.model.history.length >= 100) {
        this.model.batchTrain(32);
      }
    }, 30000);
    
    this.notifyStatus({ running: true });
  }
  
  /**
   * Stop prediction engine
   */
  stop() {
    console.log('[OneShotLive] ⏹️ Stopping...');
    this.isRunning = false;
    
    if (this.predictionInterval) clearInterval(this.predictionInterval);
    if (this.validationInterval) clearInterval(this.validationInterval);
    if (this.batchTrainInterval) clearInterval(this.batchTrainInterval);
    
    this.notifyStatus({ running: false });
  }
  
  /**
   * Make a prediction
   */
  makePrediction() {
    if (!this.isRunning) return;
    if (!this.marketFeed.hasEnoughData(50)) return;
    
    try {
      // Get recent prices
      const prices = this.marketFeed.getRecentPrices(100);
      
      // Extract features
      const extractor = new FeatureExtractor(prices);
      const featureVector = extractor.getFeatureVector();
      
      // Validate features
      const features = extractor.extractAll();
      if (!FeatureExtractor.validateFeatures(features)) {
        console.warn('[OneShotLive] Invalid features, skipping prediction');
        return;
      }
      
      // Make prediction
      const prediction = this.model.predict(featureVector);
      
      // Check if should trade (based on adaptive threshold)
      const shouldTrade = this.model.shouldTrade(prediction.confidence);
      
      // Store prediction
      const predictionRecord = {
        timestamp: Date.now(),
        direction: prediction.direction,
        confidence: prediction.confidence,
        raw_probability: prediction.raw_probability,
        features: featureVector,
        entryPrice: this.marketFeed.currentPrice,
        shouldTrade,
        confidenceThreshold: this.model.confidenceThreshold
      };
      
      this.predictionHistory.push(predictionRecord);
      if (this.predictionHistory.length > this.maxPredictionHistory) {
        this.predictionHistory.shift();
      }
      
      this.stats.totalPredictions++;
      
      // If paper trading and should trade, record paper trade
      if (this.isPaperTrading && shouldTrade) {
        this.paperTrades.push({
          ...predictionRecord,
          resolved: false
        });
        this.stats.totalTrades++;
      }
      
      // Notify UI
      if (this.onPrediction) {
        this.onPrediction({
          ...predictionRecord,
          modelStatus: this.model.getStatus()
        });
      }
      
    } catch (error) {
      console.error('[OneShotLive] Prediction error:', error);
    }
  }
  
  /**
   * Validate paper trades (check if they would have won/lost)
   */
  validatePaperTrades() {
    const now = Date.now();
    const currentPrice = this.marketFeed.currentPrice;
    
    if (!currentPrice) return;
    
    this.paperTrades = this.paperTrades.filter(trade => {
      const age = now - trade.timestamp;
      
      // Resolve after 30 seconds
      if (age >= 30000 && !trade.resolved) {
        const exitPrice = currentPrice;
        const actualDirection = exitPrice > trade.entryPrice ? 'UP' : 'DOWN';
        const win = actualDirection === trade.direction;
        
        // Update model with actual outcome
        const actualOutcome = actualDirection === 'UP' ? 1 : 0;
        this.model.update(trade.features, actualOutcome);
        
        // Update stats
        if (win) {
          this.stats.paperWins++;
        } else {
          this.stats.paperLosses++;
        }
        
        // Log result
        const pnl = win ? 0.8 : -1.0; // Assuming 80% payout
        console.log(
          `[Paper Trade] ${trade.direction} @ ${trade.confidence.toFixed(2)} → ` +
          `${win ? '✅ WIN' : '❌ LOSS'} (${actualDirection}) | ` +
          `Entry: ${trade.entryPrice.toFixed(2)} → Exit: ${exitPrice.toFixed(2)} | ` +
          `P&L: ${pnl > 0 ? '+' : ''}${pnl.toFixed(2)}`
        );
        
        // Notify UI
        if (this.onTradeResolved) {
          this.onTradeResolved({
            ...trade,
            exitPrice,
            actualDirection,
            win,
            pnl,
            age
          });
        }
        
        trade.resolved = true;
        return false; // Remove from array
      }
      
      return !trade.resolved; // Keep unresolved trades
    });
  }
  
  /**
   * Get current stats
   */
  getStats() {
    const modelStatus = this.model.getStatus();
    const marketStatus = this.marketFeed.getStatus();
    const paperWR = this.stats.totalTrades > 0 
      ? this.stats.paperWins / (this.stats.paperWins + this.stats.paperLosses)
      : 0;
    
    return {
      // System status
      running: this.isRunning,
      paperTrading: this.isPaperTrading,
      uptime: this.stats.startTime ? Date.now() - this.stats.startTime : 0,
      
      // Market feed
      marketConnected: marketStatus.connected,
      currentPrice: marketStatus.currentPrice,
      priceHistory: marketStatus.historySize,
      
      // Predictions
      totalPredictions: this.stats.totalPredictions,
      predictionHistory: this.predictionHistory.length,
      
      // Paper trading
      totalTrades: this.stats.totalTrades,
      paperWins: this.stats.paperWins,
      paperLosses: this.stats.paperLosses,
      paperWR,
      pendingTrades: this.paperTrades.length,
      
      // Model
      modelWR10: modelStatus.winRate10,
      modelWR20: modelStatus.winRate20,
      modelWR50: modelStatus.winRate50,
      modelAccuracy: modelStatus.accuracy,
      confidenceThreshold: modelStatus.confidenceThreshold,
      aggression: modelStatus.aggression,
      learningRate: modelStatus.effectiveLR,
      trainingHistory: modelStatus.historySize
    };
  }
  
  /**
   * Get recent predictions for UI display
   */
  getRecentPredictions(count = 50) {
    return this.predictionHistory.slice(-count);
  }
  
  /**
   * Enable/disable paper trading
   */
  setPaperTrading(enabled) {
    this.isPaperTrading = enabled;
    console.log(`[OneShotLive] Paper trading ${enabled ? 'ENABLED' : 'DISABLED'}`);
  }
  
  /**
   * Manual model save
   */
  saveModel() {
    const state = this.model.saveState();
    localStorage.setItem('oneshot_model_state', JSON.stringify(state));
    console.log('[OneShotLive] Model saved to localStorage');
    return state;
  }
  
  /**
   * Manual model load
   */
  loadModel() {
    const saved = localStorage.getItem('oneshot_model_state');
    if (saved) {
      const state = JSON.parse(saved);
      this.model.loadState(state);
      console.log('[OneShotLive] Model loaded from localStorage');
      return true;
    }
    return false;
  }
  
  /**
   * Notify status change (for UI updates)
   */
  notifyStatus(update) {
    if (this.onStatusUpdate) {
      this.onStatusUpdate(update);
    }
  }
  
  /**
   * Cleanup
   */
  destroy() {
    this.stop();
    this.marketFeed.destroy();
    console.log('[OneShotLive] Destroyed');
  }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OneShotLive;
}
