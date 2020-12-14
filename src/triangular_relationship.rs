use crate::trading_pair::*;
use std::fmt;

/*
 *  TriangularRelationship
 */
#[derive(Debug, Clone)]
pub struct TriangularRelationship {
  base: String,
  start: TradingPair,
  middle: TradingPair,
  end: TradingPair,
  actions: [String; 3],
  action_wrappers: [String; 3],
  intermediates: [String; 2],
}

impl fmt::Display for TriangularRelationship {
  fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
    write!(
      f,
      "{} -> {} -> {}",
      self.base, self.intermediates[0], self.intermediates[1]
    )
  }
}

impl TriangularRelationship {
  // Constructor
  pub fn new(
    base: String,
    start: TradingPair,
    middle: TradingPair,
    end: TradingPair,
  ) -> TriangularRelationship {
    let mut next_base: String;
    let mut actions: [String; 3] = ["".to_string(), "".to_string(), "".to_string()];
    let mut action_wrappers: [String; 3] = ["".to_string(), "".to_string(), "".to_string()];
    let mut intermediates: [String; 2] = ["".to_string(), "".to_string()];
    // Base -> Middle
    if base == start.get_base_asset() {
      actions[0] = "SELL".to_string();
      action_wrappers[0] = "bids".to_string();
      next_base = start.get_quote_asset();
      intermediates[0] = start.get_quote_asset()
    } else {
      actions[0] = "BUY".to_string();
      action_wrappers[0] = "asks".to_string();
      next_base = start.get_base_asset();
      intermediates[0] = start.get_base_asset()
    }

    // Middle -> End
    if next_base == middle.get_base_asset() {
      actions[1] = "SELL".to_string();
      action_wrappers[1] = "bids".to_string();
      next_base = middle.get_quote_asset();
      intermediates[1] = middle.get_quote_asset()
    } else {
      actions[1] = "BUY".to_string();
      action_wrappers[1] = "asks".to_string();
      next_base = middle.get_base_asset();
      intermediates[1] = middle.get_base_asset()
    }

    // End -> Base
    if next_base == end.get_base_asset() {
      actions[2] = "SELL".to_string();
      action_wrappers[2] = "bids".to_string();
    } else {
      actions[2] = "BUY".to_string();
      action_wrappers[2] = "asks".to_string();
    }

    TriangularRelationship {
      base,
      start,
      middle,
      end,
      actions,
      action_wrappers,
      intermediates,
    }
  }

  pub fn describe(&self) -> String {
    format!(
      "{} from {}, then {} from {} and finally {} from {}",
      self.actions[0],
      self.start.text(),
      self.actions[1],
      self.middle.text(),
      self.actions[2],
      self.end.text()
    )
  }

  pub fn get_pairs(&self) -> [String; 3] {
    [
      self.start.get_symbol(),
      self.middle.get_symbol(),
      self.end.get_symbol(),
    ]
  }

  pub fn get_trading_pairs(&self) -> [TradingPair; 3] {
    [self.start.clone(), self.middle.clone(), self.end.clone()]
  }

  pub fn get_actions(&self) -> [String; 3] {
    self.actions.clone()
  }

  pub fn text(&self) -> String {
    format!(
      "{} -> {} -> {}",
      self.base, self.intermediates[0], self.intermediates[1]
    )
  }

  pub fn get_workflow(&self) -> [(String, String); 3] {
    [
      (self.start.get_symbol(), self.action_wrappers[0].to_string()),
      (
        self.middle.get_symbol(),
        self.action_wrappers[1].to_string(),
      ),
      (self.end.get_symbol(), self.action_wrappers[2].to_string()),
    ]
  }
}
