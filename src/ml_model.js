/**
 * OneShot ML Model
 * Logistic regression with online learning
 * Adaptive thresholds based on performance
 */

class OneShotModel {
  constructor(numFeatures = 10) {
    this.numFeatures = numFeatures;
    this.weights = new Array(numFeatures).fill(0).map(() => (Math.random() - 0.5) * 0.01);
    this.bias = 0;
    this.learningRate = 0.01;
    
    // Training history
    this.history = [];
    this.maxHistory = 10000;
    
    // Performance tracking
    this.recentPredictions = [];
    this.maxRecentPredictions = 100;
    
    // Adaptive threshold system
    this.confidenceThreshold = 0.75; // Start conservative
    this.minThreshold = 0.65;
    this.maxThreshold = 0.85;
    this.thresholdAdjustRate = 0.001;
    
    // Aggression level (increases when losing)
    this.aggression = 1.0; // 1.0 = normal, 2.0 = 2x learning rate
    this.maxAggression = 3.0;
  }
  
  /**
   * Sigmoid activation function
   */
  sigmoid(z) {
    return 1 / (1 + Math.exp(-Math.max(-500, Math.min(500, z)))); // Clamp to prevent overflow
  }
  
  /**
   * Make a prediction
   * @param {Array<number>} features - Feature vector
   * @returns {Object} Prediction with direction, confidence, raw probability
   */
  predict(features) {
    if (features.length !== this.numFeatures) {
      throw new Error(`Expected ${this.numFeatures} features, got ${features.length}`);
    }
    
    // Linear combination: z = w·x + b
    const z = features.reduce((sum, val, i) => sum + val * this.weights[i], this.bias);
    
    // Apply sigmoid to get probability
    const probability = this.sigmoid(z);
    
    // Direction: UP if prob > 0.5, DOWN otherwise
    const direction = probability > 0.5 ? 'UP' : 'DOWN';
    
    // Confidence: how far from 0.5 (0.5 = uncertain, 0 or 1 = certain)
    const confidence = Math.abs(probability - 0.5) * 2;
    
    return {
      direction,
      confidence,
      raw_probability: probability,
      timestamp: Date.now()
    };
  }
  
  /**
   * Update model with actual outcome (online learning)
   * @param {Array<number>} features - Feature vector
   * @param {number} actualOutcome - 1 for UP, 0 for DOWN
   */
  update(features, actualOutcome) {
    // Get current prediction
    const prediction = this.predict(features);
    const error = actualOutcome - prediction.raw_probability;
    
    // Apply aggression multiplier to learning rate
    const effectiveLearningRate = this.learningRate * this.aggression;
    
    // Gradient descent: w = w + lr * error * x
    features.forEach((val, i) => {
      this.weights[i] += effectiveLearningRate * error * val;
    });
    this.bias += effectiveLearningRate * error;
    
    // Store in history for batch training
    this.history.push({
      features: [...features],
      outcome: actualOutcome,
      prediction: prediction.raw_probability,
      error: Math.abs(error),
      timestamp: Date.now()
    });
    
    if (this.history.length > this.maxHistory) {
      this.history.shift();
    }
    
    // Track recent performance
    const correct = (prediction.raw_probability > 0.5 && actualOutcome === 1) ||
                   (prediction.raw_probability <= 0.5 && actualOutcome === 0);
    
    this.recentPredictions.push({
      correct,
      confidence: prediction.confidence,
      timestamp: Date.now()
    });
    
    if (this.recentPredictions.length > this.maxRecentPredictions) {
      this.recentPredictions.shift();
    }
    
    // Adjust aggression and thresholds based on performance
    this.adjustParameters();
  }
  
  /**
   * Batch training on historical data
   * @param {number} batchSize - Number of samples to train on
   */
  batchTrain(batchSize = 32) {
    if (this.history.length < batchSize) return;
    
    // Sample random batch from history (with emphasis on recent + high-error samples)
    const batch = [];
    const recentWeight = 0.7; // 70% from recent data
    const numRecent = Math.floor(batchSize * recentWeight);
    const numRandom = batchSize - numRecent;
    
    // Recent samples
    const recentHistory = this.history.slice(-Math.min(200, this.history.length));
    for (let i = 0; i < numRecent; i++) {
      const idx = Math.floor(Math.random() * recentHistory.length);
      batch.push(recentHistory[idx]);
    }
    
    // Random samples (weighted by error)
    for (let i = 0; i < numRandom; i++) {
      const idx = Math.floor(Math.random() * this.history.length);
      batch.push(this.history[idx]);
    }
    
    // Train on batch
    batch.forEach(sample => {
      const z = sample.features.reduce((sum, val, i) => sum + val * this.weights[i], this.bias);
      const prediction = this.sigmoid(z);
      const error = sample.outcome - prediction;
      
      sample.features.forEach((val, i) => {
        this.weights[i] += this.learningRate * error * val;
      });
      this.bias += this.learningRate * error;
    });
  }
  
  /**
   * Adjust aggression and thresholds based on recent performance
   */
  adjustParameters() {
    if (this.recentPredictions.length < 20) return;
    
    const recentWR = this.getWinRate(20);
    const longerWR = this.getWinRate(50);
    
    // FREEZE adaptation if performing very well (≥68% WR)
    if (longerWR >= 0.68) {
      // Don't adjust anything - preserve what's working
      this.aggression = 1.0; // Keep at baseline
      return;
    }
    
    // Calculate scaling factor based on distance from 68% threshold
    // As WR approaches 68%, adjustments become gentler
    // WR @ 50% → scale = 1.0 (full adjustments)
    // WR @ 60% → scale = ~0.55 (moderate adjustments)
    // WR @ 65% → scale = ~0.20 (gentle adjustments)
    // WR @ 67% → scale = ~0.05 (minimal adjustments)
    const targetWR = 0.68;
    const minWR = 0.50;
    const distanceFromTarget = Math.max(0, targetWR - longerWR);
    const maxDistance = targetWR - minWR;
    const scalingFactor = Math.pow(distanceFromTarget / maxDistance, 2); // Quadratic falloff
    
    // Increase aggression when losing (scaled)
    if (recentWR < 0.55) {
      const aggressionIncrease = 1.0 + (0.05 * scalingFactor); // 1.00 to 1.05 based on scaling
      this.aggression = Math.min(this.maxAggression, this.aggression * aggressionIncrease);
      console.log(`[Model] Low WR (${(recentWR * 100).toFixed(1)}%) - Increasing aggression to ${this.aggression.toFixed(2)}x (scale: ${scalingFactor.toFixed(2)})`);
    } else if (recentWR > 0.65 && recentWR < 0.68) {
      // Decrease aggression when winning (but not when above 68%)
      const aggressionDecrease = 1.0 - (0.02 * scalingFactor); // 0.98 to 1.00 based on scaling
      this.aggression = Math.max(1.0, this.aggression * aggressionDecrease);
    }
    
    // Adjust confidence threshold (scaled)
    if (longerWR < 0.60) {
      // Losing: Be more selective (higher threshold, scaled)
      const scaledAdjustRate = this.thresholdAdjustRate * scalingFactor;
      this.confidenceThreshold = Math.min(
        this.maxThreshold,
        this.confidenceThreshold + scaledAdjustRate
      );
    } else if (longerWR > 0.70) {
      // Winning: Be more aggressive (lower threshold, scaled)
      const scaledAdjustRate = this.thresholdAdjustRate * scalingFactor;
      this.confidenceThreshold = Math.max(
        this.minThreshold,
        this.confidenceThreshold - scaledAdjustRate
      );
    }
  }
  
  /**
   * Get win rate over last N predictions
   * @param {number} window - Number of recent predictions
   * @returns {number} Win rate (0-1)
   */
  getWinRate(window = 50) {
    if (this.recentPredictions.length === 0) return 0.5;
    
    const recent = this.recentPredictions.slice(-window);
    const correct = recent.filter(p => p.correct).length;
    return correct / recent.length;
  }
  
  /**
   * Get model accuracy over history
   * @param {number} window - Window size
   * @returns {Object} Accuracy metrics
   */
  getAccuracy(window = 100) {
    if (this.history.length < window) {
      return { 
        accuracy: 0, 
        count: this.history.length,
        avgError: 0
      };
    }
    
    const recent = this.history.slice(-window);
    let correct = 0;
    let totalError = 0;
    
    recent.forEach(sample => {
      const predicted = sample.prediction > 0.5 ? 1 : 0;
      if (predicted === sample.outcome) correct++;
      totalError += sample.error;
    });
    
    return {
      accuracy: correct / recent.length,
      count: recent.length,
      avgError: totalError / recent.length
    };
  }
  
  /**
   * Should we trade based on prediction confidence and current threshold?
   * @param {number} confidence - Prediction confidence (0-1)
   * @returns {boolean} True if should trade
   */
  shouldTrade(confidence) {
    return confidence >= this.confidenceThreshold;
  }
  
  /**
   * Get model status for monitoring
   * @returns {Object} Model metrics
   */
  getStatus() {
    const wr10 = this.getWinRate(10);
    const wr20 = this.getWinRate(20);
    const wr50 = this.getWinRate(50);
    const accuracy = this.getAccuracy(100);
    
    return {
      historySize: this.history.length,
      recentPredictions: this.recentPredictions.length,
      winRate10: wr10,
      winRate20: wr20,
      winRate50: wr50,
      accuracy: accuracy.accuracy,
      avgError: accuracy.avgError,
      confidenceThreshold: this.confidenceThreshold,
      aggression: this.aggression,
      learningRate: this.learningRate,
      effectiveLR: this.learningRate * this.aggression
    };
  }
  
  /**
   * Reset aggression to normal (use after extended losing streak recovery)
   */
  resetAggression() {
    this.aggression = 1.0;
    console.log('[Model] Aggression reset to 1.0x');
  }
  
  /**
   * Save model state (for persistence)
   * @returns {Object} Serializable model state
   */
  saveState() {
    return {
      weights: this.weights,
      bias: this.bias,
      confidenceThreshold: this.confidenceThreshold,
      aggression: this.aggression,
      timestamp: Date.now()
    };
  }
  
  /**
   * Load model state (from persistence)
   * @param {Object} state - Previously saved state
   */
  loadState(state) {
    this.weights = state.weights;
    this.bias = state.bias;
    this.confidenceThreshold = state.confidenceThreshold || 0.75;
    this.aggression = state.aggression || 1.0;
    console.log('[Model] State loaded from checkpoint');
  }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OneShotModel;
}
