use binance::api::*;
use binance::general::*;
use binance::market::*;
use binance::model::*;
use binance::websockets::*;
use btrader::depth_cache::DepthCache;
use btrader::trader::bTrader;
use dashmap::DashMap;
use log;
use rayon::prelude::*;
use simple_logger::SimpleLogger;
use std::collections::HashMap;
use std::sync::atomic::AtomicBool;
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::Duration;
use std::time::{SystemTime, UNIX_EPOCH};

fn sum_of_squares(input: &[i32]) -> i32 {
  input
    .par_iter() // <-- just change that!
    .map(|&i| i * i * i * i)
    .sum()
}

fn market_websocket() {
  let keep_running = AtomicBool::new(true); // Used to control the event loop
  let agg_trade: String = String::from("ethbtc@depth@100ms/bnbbtc@depth@100ms");
  let mut web_socket: WebSockets<'_> = WebSockets::new(|event: WebsocketEvent| {
    match event {
      WebsocketEvent::Trade(trade) => {
        println!(
          "Symbol: {}, price: {}, qty: {}",
          trade.symbol, trade.price, trade.qty
        );
      }
      WebsocketEvent::DepthOrderBook(depth_order_book) => {
        println!(
          "Symbol: {}, Data: {:?}",
          depth_order_book.symbol, depth_order_book
        );
      }
      WebsocketEvent::OrderBook(order_book) => {
        println!(
          "1 ==> last_update_id: {}, Bids: {:?}, Ask: {:?}",
          order_book.last_update_id, order_book.bids, order_book.asks
        );
      }
      _ => (),
    };

    Ok(())
  });
  web_socket.connect(&agg_trade).unwrap(); // check error
  println!("connected");
  if let Err(e) = web_socket.event_loop(&keep_running) {
    println!("Error: {}", e);
  }
  web_socket.disconnect().unwrap();
  println!("disconnected");
}

fn market_data() {
  let market: Market = Binance::new(None, None);

  // Order books
  match market.get_depth("BNBETH&limit=1000") {
    Ok(answer) => println!("{:?}", answer.bids.len()),
    Err(e) => println!("Error: {}", e),
  }
}

fn get_epoch_ms() -> u64 {
  SystemTime::now()
    .duration_since(UNIX_EPOCH)
    .unwrap()
    .as_millis() as u64
}

fn main() {
  // // Logging
  // SimpleLogger::new().init().unwrap();
  // log::debug!("This is an example message.");
  // log::info!("This is an example message.");
  // log::warn!("This is an example message.");
  // log::error!("This is an example message.");
  // println!("{}", sum_of_squares(&[9, 9, 9, 9, 9, 9, 3]))
  // market_websocket();
  // market_data();
  let mut a: bTrader = bTrader::new("tests/config.json");
  a.run();
  // let symbols: Vec<String> = vec!["BNBBTC".to_string(), "ETHBTC".to_string()];
  // let depth = DepthCache::new(&symbols);
  // thread::sleep(Duration::from_secs(5));
  // let dep = depth.get_depth(&symbols[1]);
  // println!("{:?}", dep.asks[2]);
  // println!("{:?}", dep.asks[1]);
  // println!("{:?}", dep.asks[0]);
  // println!("{:?}", dep.bids[0]);
  // println!("{:?}", dep.bids[1]);
  // println!("{:?}", dep.bids[2]);
}
