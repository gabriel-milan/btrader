use crate::config::Configuration;
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Mutex};
use std::thread;
use telegram_bot::*;

#[derive(Debug)]
pub struct TelegramBot {
  telegram_token: String,
  telegram_user_id: i64,
  in_tx: Mutex<Sender<String>>,
  in_rx: Arc<Mutex<Receiver<String>>>,
}

impl TelegramBot {
  pub fn new(config: Configuration) -> TelegramBot {
    let (in_tx, in_rx): (Sender<String>, Receiver<String>) = mpsc::channel();
    let in_tx_mutex = Mutex::new(in_tx);
    let in_rx_mutex = Arc::new(Mutex::new(in_rx));
    TelegramBot {
      telegram_token: config.telegram_token,
      telegram_user_id: config.telegram_user_id,
      in_tx: in_tx_mutex,
      in_rx: in_rx_mutex,
    }
  }
  pub fn send_message(&self, message: String) {
    if self.in_tx.lock().unwrap().send(message.clone()).is_err() {
      println!("Failed to send message \"{}\"", message);
    };
  }
  pub fn start(&self) {
    let api = Api::new(self.telegram_token.clone());
    let chat = ChatId::new(self.telegram_user_id);
    let in_rx_clone = self.in_rx.clone();
    thread::spawn(move || bot_main(api, chat, in_rx_clone));
  }
}

#[tokio::main]
async fn bot_main(
  api: Api,
  chat: ChatId,
  in_rx: Arc<Mutex<Receiver<String>>>,
) -> Result<(), Error> {
  loop {
    if let Ok(message) = in_rx.lock().unwrap().try_recv() {
      api.spawn(chat.text(message));
    }
  }
}
