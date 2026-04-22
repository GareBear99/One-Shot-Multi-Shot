/**
 * OneShot Feature Extractor
 * Extracts predictive features from price data
 * Momentum, volatility, trend, acceleration
 */

class FeatureExtractor {
  constructor(priceHistory) {
    this.prices = priceHistory;
  }
  
  /**
   * Calculate momentum across multiple timeframes
   * @param {Array<number>} periods - Timeframes in seconds [1, 5, 10, 30]
   * @returns {Object} Momentum features
   */
  momentum(periods = [1, 5, 10, 30]) {
    const features = {};
    
    periods.forEach(p => {
      if (this.prices.length < p * 2) {
        features[`momentum_${p}s`] = 0;
        return;
      }
      
      const recent = this.prices.slice(-p);
      const older = this.prices.slice(-p * 2, -p);
      
      const recentAvg = this.average(recent);
      const olderAvg = this.average(older);
      
      // Normalized momentum (percentage change)
      features[`momentum_${p}s`] = olderAvg !== 0 ? (recentAvg - olderAvg) / olderAvg : 0;
    });
    
    return features;
  }
  
  /**
   * Calculate volatility (rolling standard deviation)
   * @param {number} window - Window size in ticks
   * @returns {Object} Volatility features
   */
  volatility(window = 30) {
    if (this.prices.length < window) {
      return { volatility: 0, volatility_normalized: 0 };
    }
    
    const recent = this.prices.slice(-window);
    const mean = this.average(recent);
    const variance = recent.reduce((sum, price) => {
      return sum + Math.pow(price - mean, 2);
    }, 0) / recent.length;
    
    const std = Math.sqrt(variance);
    const normalized = mean !== 0 ? std / mean : 0;
    
    return {
      volatility: std,
      volatility_normalized: normalized
    };
  }
  
  /**
   * Detect micro-trend using linear regression
   * @param {number} window - Window size for trend calculation
   * @returns {Object} Trend slope and R-squared
   */
  microTrend(window = 20) {
    if (this.prices.length < window) {
      return { trend: 0, trend_strength: 0 };
    }
    
    const data = this.prices.slice(-window);
    const n = data.length;
    
    // Linear regression: y = slope * x + intercept
    const sumX = (n * (n - 1)) / 2;
    const sumY = data.reduce((a, b) => a + b, 0);
    const sumXY = data.reduce((sum, y, x) => sum + x * y, 0);
    const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6;
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    
    // Calculate R-squared (trend strength)
    const yMean = sumY / n;
    const ssTotal = data.reduce((sum, y) => sum + Math.pow(y - yMean, 2), 0);
    const ssResidual = data.reduce((sum, y, x) => {
      const predicted = slope * x + intercept;
      return sum + Math.pow(y - predicted, 2);
    }, 0);
    
    const r2 = ssTotal !== 0 ? 1 - (ssResidual / ssTotal) : 0;
    
    // Normalize slope by average price
    const avgPrice = yMean;
    const normalizedSlope = avgPrice !== 0 ? slope / avgPrice : 0;
    
    return {
      trend: normalizedSlope,
      trend_strength: Math.max(0, Math.min(1, r2))
    };
  }
  
  /**
   * Calculate price acceleration (second derivative)
   * @returns {Object} Acceleration feature
   */
  priceAcceleration() {
    if (this.prices.length < 6) {
      return { acceleration: 0 };
    }
    
    const p1 = this.average(this.prices.slice(-2));
    const p2 = this.average(this.prices.slice(-4, -2));
    const p3 = this.average(this.prices.slice(-6, -4));
    
    const v1 = p1 - p2; // Recent velocity
    const v2 = p2 - p3; // Previous velocity
    const acceleration = v1 - v2; // Change in velocity
    
    // Normalize by price
    const normalizedAcceleration = p3 !== 0 ? acceleration / p3 : 0;
    
    return { acceleration: normalizedAcceleration };
  }
  
  /**
   * Calculate relative strength (recent performance vs longer term)
   * @returns {Object} Relative strength
   */
  relativeStrength() {
    if (this.prices.length < 50) {
      return { relative_strength: 0 };
    }
    
    const recent10 = this.average(this.prices.slice(-10));
    const longer50 = this.average(this.prices.slice(-50));
    
    const rs = longer50 !== 0 ? (recent10 - longer50) / longer50 : 0;
    
    return { relative_strength: rs };
  }
  
  /**
   * Price position within recent range
   * @param {number} window - Lookback window
   * @returns {Object} Price position (0 = at low, 1 = at high)
   */
  pricePosition(window = 30) {
    if (this.prices.length < window) {
      return { price_position: 0.5 };
    }
    
    const recent = this.prices.slice(-window);
    const current = this.prices[this.prices.length - 1];
    const high = Math.max(...recent);
    const low = Math.min(...recent);
    
    const position = high !== low ? (current - low) / (high - low) : 0.5;
    
    return { price_position: position };
  }
  
  /**
   * Extract all features at once
   * @returns {Object} All features combined
   */
  extractAll() {
    return {
      ...this.momentum(),
      ...this.volatility(),
      ...this.microTrend(),
      ...this.priceAcceleration(),
      ...this.relativeStrength(),
      ...this.pricePosition(),
      timestamp: Date.now()
    };
  }
  
  /**
   * Get feature vector as array (for ML model input)
   * @returns {Array<number>} Feature values in consistent order
   */
  getFeatureVector() {
    const features = this.extractAll();
    
    // Return in consistent order
    return [
      features.momentum_1s || 0,
      features.momentum_5s || 0,
      features.momentum_10s || 0,
      features.momentum_30s || 0,
      features.volatility_normalized || 0,
      features.trend || 0,
      features.trend_strength || 0,
      features.acceleration || 0,
      features.relative_strength || 0,
      features.price_position || 0
    ];
  }
  
  /**
   * Get feature names (for logging/debugging)
   * @returns {Array<string>} Feature names in order
   */
  static getFeatureNames() {
    return [
      'momentum_1s',
      'momentum_5s',
      'momentum_10s',
      'momentum_30s',
      'volatility_normalized',
      'trend',
      'trend_strength',
      'acceleration',
      'relative_strength',
      'price_position'
    ];
  }
  
  // Helper methods
  average(arr) {
    return arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
  }
  
  /**
   * Validate that features are reasonable (no NaN, Infinity)
   * @param {Object} features - Feature object to validate
   * @returns {boolean} True if valid
   */
  static validateFeatures(features) {
    for (const [key, value] of Object.entries(features)) {
      if (key === 'timestamp') continue;
      if (typeof value !== 'number' || isNaN(value) || !isFinite(value)) {
        console.warn(`[FeatureExtractor] Invalid feature ${key}:`, value);
        return false;
      }
    }
    return true;
  }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FeatureExtractor;
}
