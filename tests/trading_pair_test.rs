#[cfg(test)]
mod trading_pair_tests {
  #[test]
  fn getters_test() {
    use btrader::basics::*;
    let tp: TradingPair = TradingPair::new("BNBBTC", "BNB", "BTC", 0.01);
    assert_eq!(tp.get_symbol(), "BNBBTC");
    assert_eq!(tp.get_step(), 0.01f64);
    assert_eq!(tp.get_base_asset(), "BNB");
    assert_eq!(tp.get_quote_asset(), "BTC");
  }

  #[test]
  fn utilities_test() {
    use btrader::basics::*;
    let tp1: TradingPair = TradingPair::new("BNBBTC", "BNB", "BTC", 0.01);
    assert_eq!(tp1.has_asset("BNB"), true);
    assert_eq!(tp1.has_asset("BTC"), true);
    assert_eq!(tp1.has_asset("ETH"), false);
    assert_eq!(tp1.get_the_other("BNB"), "BTC");
    assert_eq!(tp1.get_the_other("BTC"), "BNB");
  }

  #[test]
  fn eq_test() {
    use btrader::basics::*;
    let tp1: TradingPair = TradingPair::new("BNBBTC", "BNB", "BTC", 0.01);
    let tp2: TradingPair = TradingPair::new("BTCBNB", "BTC", "BNB", 0.00001);
    assert_eq!(tp1, tp2);
  }
}
