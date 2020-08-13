import numpy as np
from otools import Logger
from btrader.core import bTrader
from threading import Timer, Thread, Lock
from queue import Queue
from time import sleep

SYMBOL_WORKERS  = 4
SAVING_WORKERS  = 1

logger_class    = Logger()
logger          = logger_class.getModuleLogger()
trader          = bTrader("bTrader.json")
running         = True
symbol_queue    = Queue()
saving_queue    = Queue()
saving_lock     = Lock()

logger.setLevel(9)
logger_class.setLevel(9)

def symbol_worker (i, trader, logger, running, symbol_queue, saving_queue):
  while running:
    if not symbol_queue.empty():
      symbol = symbol_queue.get()
      logger.debug("Worker #{} got symbol {} from queue".format(i, symbol))
      order_book = trader.getOrderBook (symbol)
      asks = order_book['asks']
      asks.reverse()
      asks = np.array(asks).astype(float)
      bids = order_book['bids']
      bids = np.array(bids).astype(float)
      arr  = np.concatenate((asks, bids))
      mean = (np.min(asks[-1][0]) + np.min(bids[0][0]))/2
      logger.info("Symbol {}: {}".format(symbol, mean))
      saving_queue.put((symbol, arr, mean))
  logger.debug("Worker #{} shutting down...".format(i))
  return True

def saving_worker (i, trader, logger, running, saving_queue, saving_lock, fname):
  while running:
    if not saving_queue.empty():
      symbol, arr, mean = saving_queue.get()
      logger.debug("Saving worker #{} got symbol {} from queue".format(i, symbol))
      saving_lock.acquire()
      logger.debug("Saving worker #{} successfully acquired file lock for reading".format(i))
      try:
        data = np.load(fname)
      except FileNotFoundError:
        data = None
        logger.debug("File did not exist, skipping reading")
      saving_lock.release()
      logger.debug("Saving worker #{} released lock after reading".format(i))
      if data and 'X_{}'.format(symbol) in data.keys():
        X = data['X_{}'.format(symbol)]
        X = np.concatenate((X, arr))
        y = data['y_{}'.format(symbol)]
        y = np.concatenate((y, [mean]))
      else:
        X = arr
        y = np.array([mean])
      logger.verbose("{}: X {}, y {}".format(symbol, X.shape, y.shape))
      saving_lock.acquire()
      logger.debug("Saving worker #{} successfully acquired file lock for writing".format(i))
      try:
        data = np.load(fname)
        flist = ["{0}=data['{0}']".format(x) for x in data.files if symbol not in x]
      except FileNotFoundError:
        data = None
        flist = []
      flist.append("X_{}=X".format(symbol))
      flist.append("y_{}=y".format(symbol))
      fstr = ', '.join(flist)
      logger.verbose("np.savez(fname, {})".format(fstr))
      eval("np.savez_compressed(fname, {})".format(fstr))
      saving_lock.release()
      logger.debug("Saving worker #{} released lock after writing".format(i))
  logger.debug("Saving worker #{} shutting down...".format(i))
  return True

def timed_requests ():
  Timer(1, timed_requests).start()
  for symbol in trader.symbols:
    logger.info("Scheduling symbol {}".format(symbol))
    symbol_queue.put(symbol)

if __name__ == '__main__':

  logger.info ("Starting data collector...")

  logger.info ("Adding symbol workers...")
  for i in range(SYMBOL_WORKERS):
    worker = Thread(target=symbol_worker, args=(i+1, trader, logger, running, symbol_queue, saving_queue))
    worker.setDaemon(True)
    worker.start()
  
  logger.info ("Adding saving workers...")
  for j in range(SAVING_WORKERS):
    worker = Thread(target=saving_worker, args=(j+1, trader, logger, running, saving_queue, saving_lock, "output.npz"))
    worker.setDaemon(True)
    worker.start()

  logger.info ("Scheduling first iteration...")
  timed_requests()

  while running:
    try:
      pass
    except KeyboardInterrupt:
      running = False
