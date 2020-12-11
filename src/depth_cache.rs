use binance::api::*;
use binance::market::*;
use binance::model::*;
use binance::websockets::*;
use console::style;
use indicatif::ProgressBar;
use rayon::prelude::*;
use std::collections::{HashMap, VecDeque};
use std::sync::atomic::AtomicBool;
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, RwLock};
use std::thread;

#[derive(Debug, Clone)]
pub struct LocalOrderBook {
  pub first_event: bool,
  pub last_update_id: u64,
  pub event_time: u64,
  pub bids: Vec<Bids>,
  pub asks: Vec<Asks>,
}

#[derive(Debug)]
pub struct DepthCache {
  map: Arc<RwLock<HashMap<String, LocalOrderBook>>>,
  in_tx: Sender<String>,
  out_rx: Receiver<LocalOrderBook>,
}

impl DepthCache {
  // Constructor
  pub fn new(symbol_vec: &Vec<String>) -> DepthCache {
    let symbols = symbol_vec.clone();
    let queue: Arc<RwLock<VecDeque<DepthOrderBookEvent>>> = Arc::new(RwLock::new(VecDeque::new()));
    let global_map: Arc<RwLock<HashMap<String, LocalOrderBook>>> =
      Arc::new(RwLock::new(HashMap::new()));
    let map = global_map.clone();
    /*
     * Starts thread that enqueues diff depth stream events
     */
    println!(
      "{} Starting thread for enqueueing diff depth stream events...",
      style("[5/7]").bold().dim(),
    );
    start_enqueue_diffs(&symbols, queue.clone());
    /*
     * Starts thread that keep updating the HashMap using the enqueued data
     */
    thread::spawn(move || {
      // Initialize stuff
      let market: Market = Binance::new(None, None);
      // Initialize keys on Dashmap
      println!(
        "{} Getting snapshots for starter depth books...",
        style("[6/7]").bold().dim(),
      );
      let pb = ProgressBar::new(symbols.len() as u64);
      symbols.par_iter().for_each(|symbol| {
        let order_book: OrderBook = get_snapshot(&market, symbol);
        let mut m = match map.write() {
          Ok(v) => v,
          Err(e) => panic!("Failed to get map for writing while enqueueing data: {}", e),
        };
        m.insert(
          format!("{}", symbol),
          LocalOrderBook {
            first_event: true,
            last_update_id: order_book.last_update_id,
            event_time: 0,
            bids: order_book.bids,
            asks: order_book.asks,
          },
        );
        pb.inc(1);
      });
      pb.finish_and_clear();
      print!(
        "{} Processing depth stream events...",
        style("[7/7]").bold().dim(),
      );
      // Loop processing queue
      let mut processed = false;
      loop {
        let mut q = match queue.write() {
          Ok(v) => v,
          Err(e) => panic!(
            "Failed to get queue for write while processing queue: {}",
            e
          ),
        };
        if !processed {
          if q.len() == 0 {
            processed = true;
            println!(" done! Trader is now operating")
          }
        }
        match q.pop_front() {
          Some(event) => {
            let mut this_map = match map.write() {
              Ok(m) => m,
              Err(e) => panic!("Failed to get map for write while processing queue: {}", e),
            };
            let mut local_order_book = this_map.get_mut(&event.symbol).unwrap();
            // First event for this symbol (step 5)
            if local_order_book.first_event {
              if (event.first_update_id <= local_order_book.last_update_id + 1)
                && (event.final_update_id >= local_order_book.last_update_id + 1)
              {
                // Update
                update_local_order_book(event, &mut local_order_book);
              }
            }
            // Every other event after first one (step 6)
            else {
              if event.first_update_id == local_order_book.last_update_id + 1 {
                // Update
                update_local_order_book(event, &mut local_order_book);
              }
            }
          }
          None => (),
        };
      }
    });
    let (in_tx, in_rx): (Sender<String>, Receiver<String>) = mpsc::channel();
    let (out_tx, out_rx): (Sender<LocalOrderBook>, Receiver<LocalOrderBook>) = mpsc::channel();
    let read_map = global_map.clone();
    /*
     * Starts thread that will handle requests for depth cache
     */
    thread::spawn(move || loop {
      if let Ok(symbol) = in_rx.try_recv() {
        let this_map = read_map.read().unwrap();
        let res = this_map.get(&symbol).unwrap();
        out_tx.send(res.clone()).unwrap();
      }
    });
    DepthCache {
      map: global_map,
      in_tx: in_tx,
      out_rx: out_rx,
    }
  }
  // Requires data from HashMap
  pub fn get_depth(&self, symbol: &String) -> LocalOrderBook {
    if let Err(e) = self.in_tx.send(symbol.clone()) {
      panic!("Failed to send data to thread, err={}", e);
    };
    self.out_rx.recv().unwrap()
  }
}

fn get_snapshot(market: &Market, symbol: &String) -> OrderBook {
  let res = match market.get_depth(format!("{}&limit=100", symbol)) {
    Ok(answer) => answer,
    Err(e) => panic!(
      "Failed to get OrderBook for symbol {}. Error: {}",
      symbol, e
    ),
  };
  res
}

fn start_enqueue_diffs(symbols: &Vec<String>, queue: Arc<RwLock<VecDeque<DepthOrderBookEvent>>>) {
  let thread_symbols = symbols.clone();
  thread::spawn(move || {
    let mut start_str: String;
    if thread_symbols.len() > 0 {
      start_str = format!("{}@depth@100ms", thread_symbols[0].to_lowercase());
    } else {
      panic!("Must have at least one symbol!");
    }
    for symbol in &thread_symbols[1..thread_symbols.len()] {
      start_str.push_str(&format!("/{}@depth@100ms", symbol.to_lowercase()));
    }
    let keep_running = AtomicBool::new(true);
    let mut web_socket: WebSockets<'_> = WebSockets::new(|event: WebsocketEvent| {
      match event {
        WebsocketEvent::DepthOrderBook(depth_order_book) => {
          queue.write().unwrap().push_back(depth_order_book);
          // println!("Adding to queue: {}", queue.read().unwrap().len());
        }
        _ => (),
      };
      Ok(())
    });
    web_socket.connect(&start_str).unwrap(); // check error
    if let Err(e) = web_socket.event_loop(&keep_running) {
      panic!("Error while enqueuing diffs: {}", e);
    }
    web_socket.disconnect().unwrap();
    // println!("Enqueue thread disconnected.");
  });
}

fn update_local_order_book(event: DepthOrderBookEvent, lob: &mut LocalOrderBook) -> () {
  // Update first_event
  lob.first_event = false;
  // Update last_update_id
  lob.last_update_id = event.final_update_id;
  // Update event_time
  lob.event_time = event.event_time;
  // Iterate over event bids
  for ev_bid in &event.bids {
    // Find bid price on LocalOrderBook bids
    let mut found: bool = false;
    let mut remove: bool = false;
    for lob_bid in lob.bids.iter_mut() {
      // If matches
      if lob_bid.price == ev_bid.price {
        // If quantity differs from zero, replace
        found = true;
        if ev_bid.qty != 0.0 {
          lob_bid.qty = ev_bid.qty;
        }
        // If quantity is zero, remove from Vec
        else {
          remove = true;
        }
        break;
      };
    }
    // Finally remove if needed
    if found && remove {
      if let Some(pos) = lob.bids.iter().position(|x| x.price == ev_bid.price) {
        lob.bids.remove(pos);
      }
    }
    // Add if not found
    if !found {
      lob.bids.push(ev_bid.clone());
      // Sort by price
      lob
        .bids
        .sort_by(|a, b| b.price.partial_cmp(&a.price).unwrap());
    }
  }
  // Iterate over event asks
  for ev_ask in &event.asks {
    // Find ask price on LocalOrderBook asks
    let mut found: bool = false;
    let mut remove: bool = false;
    for lob_ask in lob.asks.iter_mut() {
      // If matches
      if lob_ask.price == ev_ask.price {
        // If quantity differs from zero, replace
        found = true;
        if ev_ask.qty != 0.0 {
          lob_ask.qty = ev_ask.qty;
        }
        // If quantity is zero, remove from Vec
        else {
          remove = true;
        }
        break;
      };
    }
    // Finally remove if needed
    if found && remove {
      if let Some(pos) = lob.asks.iter().position(|x| x.price == ev_ask.price) {
        lob.asks.remove(pos);
      }
    }
    // Add if not found
    if !found {
      lob.asks.push(ev_ask.clone());
      // Sort by price
      lob
        .asks
        .sort_by(|a, b| a.price.partial_cmp(&b.price).unwrap());
    }
  }
}
