use btrader::trader::bTrader;
use std::env;

fn main() {
  let args: Vec<String> = env::args().collect();
  let trader: bTrader = bTrader::new(&args[1]);
  trader.run();
}
