use crate::calculation_cluster::CalculationCluster;
use crate::config::Configuration;
use crate::depth_cache::DepthCache;
use crate::trading_pair::TradingPair;
use crate::triangular_relationship::TriangularRelationship;
use binance::api::*;
use binance::general::*;
use binance::model::*;
use console::style;
use std::collections::HashMap;
use std::fmt;

/*
 *  bTrader
 */
#[allow(non_camel_case_types)]
pub struct bTrader {
  calculation_cluster: CalculationCluster,
}

impl fmt::Display for bTrader {
  fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
    write!(f, "<bTrader>")
  }
}

impl bTrader {
  // Constructor
  pub fn new(config_path: &str) -> bTrader {
    // Starting with configuration
    let config: Configuration = Configuration::new(config_path);
    // Getting information from Binance...
    print!("{} Connecting to Binance...", style("[1/7]").bold().dim(),);
    let general: General = Binance::new(None, None);
    println!(" Successfully connected!");
    // Get trading pairs
    print!("{} Getting trading pairs...", style("[2/7]").bold().dim(),);
    let mut pairs: Vec<TradingPair> = Vec::new();
    let result = match general.exchange_info() {
      Ok(answer) => answer,
      Err(e) => panic!("Error on getting exchange info: {}", e),
    };
    for symbol in &result.symbols {
      // Checks if symbol is currently trading
      if symbol.status == "TRADING" {
        let mut step: f64 = 0.0;
        // Get step for this symbol
        for filter in &symbol.filters {
          if let Filters::LotSize {
            min_qty: _,
            max_qty: _,
            step_size,
          } = filter
          {
            step = step_size.parse().unwrap()
          };
        }
        pairs.push(TradingPair::new(
          symbol.symbol.to_string(),
          symbol.base_asset.to_string(),
          symbol.quote_asset.to_string(),
          step,
        ));
      }
    }
    println!(" {} symbols found!", pairs.len());
    // Get start/end pairs
    print!(
      "{} Getting arbitrage deal starters...",
      style("[3/7]").bold().dim(),
    );
    let mut starters: Vec<TradingPair> = Vec::new();
    for pair in &pairs {
      if pair.has_asset(config.investment_base.to_string()) {
        starters.push(pair.clone());
      }
    }
    println!(
      " {} symbols could start or end a triangular operation.",
      starters.len()
    );
    // Get relationships
    print!(
      "{} Computing triangular relationships...",
      style("[4/7]").bold().dim(),
    );
    let mut relationships: HashMap<String, TriangularRelationship> = HashMap::new();
    let mut socket_pairs: Vec<String> = Vec::new();
    for (i, start_pair) in starters[0..starters.len() - 1].iter().enumerate() {
      for end_pair in starters[i + 1..starters.len()].iter() {
        let middle = TradingPair::new(
          "".to_string(),
          start_pair.get_the_other(config.investment_base.to_string()),
          end_pair.get_the_other(config.investment_base.to_string()),
          0.0,
        );
        for middle_pair in pairs.iter() {
          if middle_pair == &middle {
            // Add start pair to sockets list
            if !socket_pairs.contains(&start_pair.get_symbol()) {
              socket_pairs.push(start_pair.get_symbol());
            }
            // Add middle pair to sockets list
            if !socket_pairs.contains(&middle_pair.get_symbol()) {
              socket_pairs.push(middle_pair.get_symbol());
            }
            // Add end pair to sockets list
            if !socket_pairs.contains(&end_pair.get_symbol()) {
              socket_pairs.push(end_pair.get_symbol());
            }
            relationships.insert(
              format!(
                "{} -> {} -> {}",
                start_pair.get_symbol(),
                middle_pair.get_symbol(),
                end_pair.get_symbol()
              ),
              TriangularRelationship::new(
                config.investment_base.to_string(),
                TradingPair::new(
                  start_pair.get_symbol(),
                  start_pair.get_base_asset(),
                  start_pair.get_quote_asset(),
                  start_pair.get_step(),
                ),
                TradingPair::new(
                  middle_pair.get_symbol(),
                  middle_pair.get_base_asset(),
                  middle_pair.get_quote_asset(),
                  middle_pair.get_step(),
                ),
                TradingPair::new(
                  end_pair.get_symbol(),
                  end_pair.get_base_asset(),
                  end_pair.get_quote_asset(),
                  end_pair.get_step(),
                ),
              ),
            );
            break;
          }
        }
      }
    }
    println!(
      " {} triangular relationships found, will have to handle {} websockets",
      relationships.len(),
      socket_pairs.len()
    );
    let depth_cache = DepthCache::new(&socket_pairs, 8, 1);
    let calculation_cluster = CalculationCluster::new(relationships, depth_cache, config);
    bTrader {
      calculation_cluster,
    }
  }
  // Execute
  pub fn run(&self) {
    self.calculation_cluster.start();
  }
}
