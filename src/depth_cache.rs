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
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::Duration;

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
  in_tx: Mutex<Sender<String>>,
  out_rx: Mutex<Receiver<LocalOrderBook>>,
}

impl DepthCache {
  // Constructor
  pub fn new(
    symbol_vec: &[String],
    threads_enqueue: u32,
    threads_process_queue: u32,
  ) -> DepthCache {
    let symbols = symbol_vec.to_owned();
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
    start_enqueue_diffs(&symbols, queue.clone(), threads_enqueue);
    /*
     * Starts threads that keep updating the HashMap using the enqueued data
     */
    println!(
      "{} Getting snapshots for starter depth books...",
      style("[6/7]").bold().dim(),
    );
    // Initialize stuff
    let market: Market = Binance::new(None, None);
    // Initialize keys on Dashmap
    let pb = ProgressBar::new(symbols.len() as u64);
    symbols.par_iter().for_each(|symbol| {
      let order_book: OrderBook = get_snapshot(&market, symbol);
      let mut m = match map.write() {
        Ok(v) => v,
        Err(e) => panic!("Failed to get map for writing while enqueueing data: {}", e),
      };
      m.insert(
        symbol.to_string(),
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
    for _ in 0..threads_process_queue {
      let map_clone = map.clone();
      let queue_clone = queue.clone();
      thread::spawn(move || {
        // Loop processing queue
        let mut processed = false;
        loop {
          let mut q = match queue_clone.write() {
            Ok(v) => v,
            Err(e) => panic!(
              "Failed to get queue for write while processing queue: {}",
              e
            ),
          };
          // println!("Queue size: {}", q.len());
          if !processed && q.len() == 0 {
            processed = true;
            println!(" done! Trader is now operating")
          }
          if let Some(event) = q.pop_front() {
            let mut this_map = match map_clone.write() {
              Ok(m) => m,
              Err(e) => panic!("Failed to get map for write while processing queue: {}", e),
            };
            let mut local_order_book = this_map.get_mut(&event.symbol).unwrap();
            // First event for this symbol (step 5)
            if local_order_book.first_event {
              if (event.first_update_id <= local_order_book.last_update_id + 1)
                && (event.final_update_id > local_order_book.last_update_id)
              {
                // Update
                update_local_order_book(event, &mut local_order_book);
              }
            }
            // Every other event after first one (step 6)
            else if event.first_update_id == local_order_book.last_update_id + 1 {
              // Update
              // println!(
              //   "Updating symbol {}, queue length is {}",
              //   event.symbol,
              //   q.len()
              // );
              update_local_order_book(event, &mut local_order_book);
            }
          };
        }
      });
    }
    let (in_tx, in_rx): (Sender<String>, Receiver<String>) = mpsc::channel();
    let (out_tx, out_rx): (Sender<LocalOrderBook>, Receiver<LocalOrderBook>) = mpsc::channel();
    let in_tx_mutex = Mutex::new(in_tx);
    let out_rx_mutex = Mutex::new(out_rx);
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
      in_tx: in_tx_mutex,
      out_rx: out_rx_mutex,
    }
  }
  // Requires data from HashMap
  pub fn get_depth(&self, symbol: &str) -> LocalOrderBook {
    if let Err(e) = self.in_tx.lock().unwrap().send(symbol.to_string()) {
      panic!("Failed to send data to thread, err={}", e);
    };
    self.out_rx.lock().unwrap().recv().unwrap()
  }
}

fn get_snapshot(market: &Market, symbol: &str) -> OrderBook {
  match market.get_depth(format!("{}&limit=100", symbol)) {
    Ok(answer) => answer,
    Err(e) => panic!(
      "Failed to get OrderBook for symbol {}. Error: {}",
      symbol, e
    ),
  }
}

fn start_enqueue_diffs(
  symbols: &[String],
  queue: Arc<RwLock<VecDeque<DepthOrderBookEvent>>>,
  threads_enqueue: u32,
) {
  let mut symbols_clone = symbols.to_vec().into_iter().peekable();
  let chunk_size = symbols_clone.len() / threads_enqueue as usize;
  while symbols_clone.peek().is_some() {
    let chunk: Vec<String> = symbols_clone.by_ref().take(chunk_size).collect();
    let thread_symbols = chunk.clone();
    // println!("Thread symbols: {:?}", thread_symbols);
    let thread_queue = queue.clone();
    thread::spawn(move || {
      let mut endpoints: Vec<String> = Vec::new();
      for symbol in thread_symbols.iter() {
        endpoints.push(format!("{}@depth@100ms", symbol.to_lowercase()));
      }
      loop {
        let keep_running = AtomicBool::new(true);
        let mut web_socket: WebSockets<'_> = WebSockets::new(|event: WebsocketEvent| {
          if let WebsocketEvent::DepthOrderBook(depth_order_book) = event {
            thread_queue.write().unwrap().push_back(depth_order_book);
            // println!("Adding to queue: {}", queue.read().unwrap().len());
          };
          Ok(())
        });
        web_socket.connect_multiple_streams(&endpoints).unwrap(); // check error
        if web_socket.event_loop(&keep_running).is_err() {
          thread::sleep(Duration::from_secs(1));
        }
        if web_socket.disconnect().is_err() {}
        // println!("Enqueue thread disconnected.");
      }
    });
  }
}

fn update_local_order_book(event: DepthOrderBookEvent, lob: &mut LocalOrderBook) {
  // Update first_event
  lob.first_event = false;
  // Update last_update_id
  lob.last_update_id = event.final_update_id;
  // Update event_time
  lob.event_time = event.event_time;
  if event.symbol == "ETHBTC" {
    // println!("lob {}, ev {}", lob.event_time, event.event_time);
  }
  // Iterate over event bids
  for ev_bid in &event.bids {
    // Find bid price on LocalOrderBook bids
    let mut found: bool = false;
    let mut remove: bool = false;
    for lob_bid in lob.bids.iter_mut() {
      // If matches
      if (lob_bid.price - ev_bid.price).abs() < f64::EPSILON {
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
      if let Some(pos) = lob
        .bids
        .iter()
        .position(|x| (x.price - ev_bid.price).abs() < f64::EPSILON)
      {
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
      if (lob_ask.price - ev_ask.price).abs() < f64::EPSILON {
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
      if let Some(pos) = lob
        .asks
        .iter()
        .position(|x| (x.price - ev_ask.price).abs() < f64::EPSILON)
      {
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
