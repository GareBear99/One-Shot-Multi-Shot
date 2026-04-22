/**
 * OneShot Market Data Feed
 * Real-time price data via Binance WebSocket
 * Auto-reconnect, buffering, stability features
 */

class MarketFeed {
  constructor(symbol = 'btcusdt', maxHistory = 1000) {
    this.symbol = symbol.toLowerCase();
    this.ws = null;
    this.priceHistory = [];
    this.maxHistory = maxHistory;
    this.currentPrice = null;
    this.listeners = [];
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000; // Start with 1 second
    this.lastMessageTime = null;
    this.healthCheckInterval = null;
    
    this.connect();
    this.startHealthCheck();
  }
  
  connect() {
    const url = `wss://stream.binance.com:9443/ws/${this.symbol}@trade`;
    console.log(`[MarketFeed] Connecting to ${url}...`);
    
    try {
      this.ws = new WebSocket(url);
      
      this.ws.onopen = () => {
        console.log('[MarketFeed] ✅ Connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.notifyListeners({ type: 'connected' });
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const price = parseFloat(data.p);
          const timestamp = data.T;
          const volume = parseFloat(data.q || 0);
          
          if (isNaN(price)) {
            console.warn('[MarketFeed] Invalid price received:', data);
            return;
          }
          
          this.currentPrice = price;
          this.lastMessageTime = Date.now();
          
          this.priceHistory.push({ 
            price, 
            timestamp, 
            volume,
            tradeId: data.t 
          });
          
          // Maintain buffer size
          if (this.priceHistory.length > this.maxHistory) {
            this.priceHistory.shift();
          }
          
          // Notify listeners of new price
          this.notifyListeners({ 
            type: 'price', 
            price, 
            timestamp, 
            volume 
          });
        } catch (error) {
          console.error('[MarketFeed] Error parsing message:', error);
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('[MarketFeed] ❌ WebSocket error:', error);
        this.isConnected = false;
      };
      
      this.ws.onclose = (event) => {
        console.log(`[MarketFeed] Connection closed (code: ${event.code})`);
        this.isConnected = false;
        this.notifyListeners({ type: 'disconnected' });
        this.attemptReconnect();
      };
      
    } catch (error) {
      console.error('[MarketFeed] Failed to create WebSocket:', error);
      this.attemptReconnect();
    }
  }
  
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[MarketFeed] Max reconnection attempts reached. Giving up.');
      this.notifyListeners({ type: 'error', message: 'Failed to reconnect after multiple attempts' });
      return;
    }
    
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
    
    console.log(`[MarketFeed] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }
  
  startHealthCheck() {
    // Check for stale data every 10 seconds
    this.healthCheckInterval = setInterval(() => {
      if (this.isConnected && this.lastMessageTime) {
        const timeSinceLastMessage = Date.now() - this.lastMessageTime;
        if (timeSinceLastMessage > 10000) {
          console.warn(`[MarketFeed] No data received for ${timeSinceLastMessage}ms. Reconnecting...`);
          this.disconnect();
          this.connect();
        }
      }
    }, 10000);
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }
  
  destroy() {
    this.disconnect();
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
    this.listeners = [];
  }
  
  // Subscribe to feed updates
  subscribe(callback) {
    if (typeof callback !== 'function') {
      throw new Error('Callback must be a function');
    }
    this.listeners.push(callback);
    
    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }
  
  notifyListeners(data) {
    this.listeners.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error('[MarketFeed] Listener error:', error);
      }
    });
  }
  
  // Get recent prices (default: last 100)
  getRecentPrices(count = 100) {
    return this.priceHistory
      .slice(-count)
      .map(d => d.price);
  }
  
  // Get recent data with timestamps
  getRecentData(count = 100) {
    return this.priceHistory.slice(-count);
  }
  
  // Get current status
  getStatus() {
    return {
      connected: this.isConnected,
      symbol: this.symbol,
      currentPrice: this.currentPrice,
      historySize: this.priceHistory.length,
      lastUpdate: this.lastMessageTime,
      timeSinceUpdate: this.lastMessageTime ? Date.now() - this.lastMessageTime : null
    };
  }
  
  // Check if we have enough data for predictions
  hasEnoughData(minSamples = 50) {
    return this.priceHistory.length >= minSamples;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MarketFeed;
}
