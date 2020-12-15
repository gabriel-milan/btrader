use serde::{Deserialize, Serialize};
use std::error::Error;
use std::fmt;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Configuration {
  pub api_key: String,
  pub api_secret: String,
  pub investment_base: String,
  pub investment_min: f64,
  pub investment_max: f64,
  pub investment_step: f64,
  pub trading_enabled: bool,
  pub trading_execution_cap: i32,
  pub trading_taker_fee: f64,
  pub trading_profit_threshold: f64,
  pub trading_age_threshold: u64,
  pub depth_size: i32,
  pub telegram_enabled: bool,
  pub telegram_token: String,
  pub telegram_user_id: i64,
}

impl fmt::Display for Configuration {
  fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
    write!(f, "<bTrader Configuration>")
  }
}

impl Configuration {
  // Constructor
  pub fn new(config_path: &str) -> Configuration {
    match Configuration::parse_config_file(config_path) {
      Ok(v) => v,
      Err(e) => panic!("Failed to parse configuration file, error is {}", e),
    }
  }
  // Parse config
  fn parse_config_file<P: AsRef<Path>>(path: P) -> Result<Configuration, Box<dyn Error>> {
    let file = File::open(path)?;
    let reader = BufReader::new(file);
    let u: Configuration = serde_json::from_reader(reader)?;
    Ok(u)
  }
}
