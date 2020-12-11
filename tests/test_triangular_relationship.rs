#[cfg(test)]
mod triangular_relationship_tests {
  #[test]
  fn getters_test() {
    use btrader::trading_pair::TradingPair;
    use btrader::triangular_relationship::TriangularRelationship;
    let tp1: TradingPair = TradingPair::new(
      "BNBBTC".to_string(),
      "BNB".to_string(),
      "BTC".to_string(),
      0.01,
    );
    let tp2: TradingPair = TradingPair::new(
      "ETHBTC".to_string(),
      "ETH".to_string(),
      "BNB".to_string(),
      0.001,
    );
    let tp3: TradingPair = TradingPair::new(
      "ETHBNB".to_string(),
      "ETH".to_string(),
      "BTC".to_string(),
      0.001,
    );
    let triang: TriangularRelationship =
      TriangularRelationship::new("BTC".to_string(), tp1, tp2, tp3);
    assert_eq!(
      triang.describe(),
      "BUY from BNB/BTC, then BUY from ETH/BNB and finally SELL from ETH/BTC"
    );
    assert_eq!(
      triang.get_pairs(),
      [
        "BNBBTC".to_string(),
        "ETHBTC".to_string(),
        "ETHBNB".to_string()
      ]
    );
    assert_eq!(triang.text(), "BTC -> BNB -> ETH");
    assert_eq!(
      triang.get_workflow(),
      [
        ("BNBBTC".to_string(), "asks".to_string()),
        ("ETHBTC".to_string(), "asks".to_string()),
        ("ETHBNB".to_string(), "bids".to_string())
      ]
    );
  }
}
