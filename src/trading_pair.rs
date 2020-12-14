use binance::model::*;
use std::fmt;
use std::time::SystemTime;
/*
 *  TradingPair
 */
#[derive(Debug, Clone)]
pub struct TradingPair {
  symbol: String,
  base_asset: String,
  quote_asset: String,
  step: f64,
  initialized: bool,
  asks: Vec<Asks>,
  bids: Vec<Bids>,
  timestamp: SystemTime,
}

impl fmt::Display for TradingPair {
  fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
    write!(f, "<TradingPair {}/{}>", self.base_asset, self.quote_asset)
  }
}

impl TradingPair {
  // Constructor
  pub fn new(symbol: String, base_asset: String, quote_asset: String, step: f64) -> TradingPair {
    TradingPair {
      symbol,
      base_asset,
      quote_asset,
      step,
      initialized: false,
      asks: Vec::new(),
      bids: Vec::new(),
      timestamp: SystemTime::now(),
    }
  }
  // Setters
  pub fn update(&mut self, timestamp: SystemTime, asks: Vec<Asks>, bids: Vec<Bids>) {
    self.asks = asks;
    self.bids = bids;
    self.timestamp = timestamp;
    self.initialized = true;
  }
  // Getters
  pub fn get_symbol(&self) -> String {
    self.symbol.to_string()
  }
  pub fn get_step(&self) -> f64 {
    self.step
  }
  pub fn get_base_asset(&self) -> String {
    self.base_asset.to_string()
  }
  pub fn get_quote_asset(&self) -> String {
    self.quote_asset.to_string()
  }
  // Utilities
  pub fn has_asset(&self, asset: String) -> bool {
    if (asset == self.quote_asset) || (asset == self.base_asset) {
      return true;
    }
    false
  }
  pub fn get_the_other(&self, asset: String) -> String {
    if asset == self.quote_asset {
      self.base_asset.to_string()
    } else if asset == self.base_asset {
      self.quote_asset.to_string()
    } else {
      "".to_string()
    }
  }

  pub fn text(&self) -> String {
    format!("{}/{}", self.base_asset, self.quote_asset)
  }
}

// Eq overloading
impl PartialEq for TradingPair {
  fn eq(&self, other: &Self) -> bool {
    if ((other.quote_asset == self.quote_asset) && (other.base_asset == self.base_asset))
      || ((other.quote_asset == self.base_asset) && (other.base_asset == self.quote_asset))
    {
      return true;
    }
    false
  }
}
impl Eq for TradingPair {}
