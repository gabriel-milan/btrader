#[cfg(test)]
mod trading_pair_tests {
  #[test]
  fn getters_test() {
    use btrader::trading_pair::*;
    let tp: TradingPair = TradingPair::new(
      "BNBBTC".to_string(),
      "BNB".to_string(),
      "BTC".to_string(),
      0.01,
    );
    assert_eq!(tp.get_symbol(), "BNBBTC");
    assert_eq!(tp.get_step(), 0.01f64);
    assert_eq!(tp.get_base_asset(), "BNB");
    assert_eq!(tp.get_quote_asset(), "BTC");
  }

  #[test]
  fn utilities_test() {
    use btrader::trading_pair::*;
    let tp1: TradingPair = TradingPair::new(
      "BNBBTC".to_string(),
      "BNB".to_string(),
      "BTC".to_string(),
      0.01,
    );
    assert_eq!(tp1.has_asset("BNB".to_string()), true);
    assert_eq!(tp1.has_asset("BTC".to_string()), true);
    assert_eq!(tp1.has_asset("ETH".to_string()), false);
    assert_eq!(tp1.get_the_other("BNB".to_string()), "BTC");
    assert_eq!(tp1.get_the_other("BTC".to_string()), "BNB");
  }

  #[test]
  fn eq_test() {
    use btrader::trading_pair::*;
    let tp1: TradingPair = TradingPair::new(
      "BNBBTC".to_string(),
      "BNB".to_string(),
      "BTC".to_string(),
      0.01,
    );
    let tp2: TradingPair = TradingPair::new(
      "BTCBNB".to_string(),
      "BTC".to_string(),
      "BNB".to_string(),
      0.00001,
    );
    assert_eq!(tp1, tp2);
  }

  #[test]
  fn text_test() {
    use btrader::trading_pair::*;
    let tp1: TradingPair = TradingPair::new(
      "BNBBTC".to_string(),
      "BNB".to_string(),
      "BTC".to_string(),
      0.01,
    );
    assert_eq!(tp1.text(), "BNB/BTC");
  }
}
