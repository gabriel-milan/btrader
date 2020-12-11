#[cfg(test)]
mod config_tests {
  #[test]
  fn attributes_test() {
    use btrader::config::*;
    let cfg: Configuration = Configuration::new("config/sample_config.json");
    assert_eq!(cfg.api_key, "your-api-key-here");
    assert_eq!(cfg.api_secret, "your-api-secret-here");
    assert_eq!(cfg.investment_base, "BTC");
    assert_eq!(cfg.investment_min, 0.001);
    assert_eq!(cfg.investment_max, 0.0015);
    assert_eq!(cfg.investment_step, 0.0001);
    assert_eq!(cfg.trading_enabled, false);
    assert_eq!(cfg.trading_execution_cap, 1);
    assert_eq!(cfg.trading_taker_fee, 0.1);
    assert_eq!(cfg.trading_profit_threshold, 0.15);
    assert_eq!(cfg.trading_age_threshold, 100);
    assert_eq!(cfg.depth_size, 20);
    assert_eq!(cfg.telegram_token, "your-telegram-bot-token");
    assert_eq!(cfg.telegram_user_id, 0);
  }
}
