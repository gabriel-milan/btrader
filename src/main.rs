use btrader::trader::bTrader;

fn main() {
  let trader: bTrader = bTrader::new("tests/config.json");
  trader.run();
}
