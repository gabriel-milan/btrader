use std::fmt;

/*
 *  TradingPair
 */
#[derive(Debug)]
pub struct TradingPair<'a> {
  symbol: &'a str,
  base_asset: &'a str,
  quote_asset: &'a str,
  step: f64,
}

impl fmt::Display for TradingPair<'_> {
  fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
    write!(f, "<TradingPair {}/{}>", self.base_asset, self.quote_asset)
  }
}

impl TradingPair<'_> {
  // Constructor
  pub fn new<'a>(
    symbol: &'a str,
    base_asset: &'a str,
    quote_asset: &'a str,
    step: f64,
  ) -> TradingPair<'a> {
    TradingPair {
      symbol: symbol,
      base_asset: base_asset,
      quote_asset: quote_asset,
      step: step,
    }
  }
  // Getters
  pub fn get_symbol(&self) -> &str {
    self.symbol
  }
  pub fn get_step(&self) -> f64 {
    self.step
  }
  pub fn get_base_asset(&self) -> &str {
    self.base_asset
  }
  pub fn get_quote_asset(&self) -> &str {
    self.quote_asset
  }
  // Utilities
  pub fn has_asset(&self, asset: &str) -> bool {
    if (asset == self.quote_asset) || (asset == self.base_asset) {
      return true;
    }
    false
  }
  pub fn get_the_other(&self, asset: &str) -> &str {
    if asset == self.quote_asset {
      return self.base_asset;
    } else if asset == self.base_asset {
      return self.quote_asset;
    } else {
      return "";
    }
  }
}

// Eq overloading
impl PartialEq for TradingPair<'_> {
  fn eq(&self, other: &Self) -> bool {
    if ((other.quote_asset == self.quote_asset) && (other.base_asset == self.base_asset))
      || ((other.quote_asset == self.base_asset) && (other.base_asset == self.quote_asset))
    {
      return true;
    }
    false
  }
}
impl Eq for TradingPair<'_> {}
