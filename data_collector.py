import struct
import numpy as np
from time import sleep
from queue import Queue
from redis import Redis
from otools import Logger
from btrader.core import bTrader
from threading import Timer, Thread, Event, Lock

SYMBOL_WORKERS  = 8
SAVING_WORKERS  = 8

logger_class    = Logger()
logger          = logger_class.getModuleLogger()
trader          = bTrader("bTrader.json")
running         = True
symbol_queue    = Queue()
saving_queue    = Queue()
locks           = {}

logger.setLevel(9)
logger_class.setLevel(9)

#
# Extending Thread
#
class StoppableThread(Thread):
  """Thread class with a stop() method. The thread itself has to check
  regularly for the stopped() condition."""

  def __init__(self,  *args, **kwargs):
    super(StoppableThread, self).__init__(*args, **kwargs)
    self._stop_event = Event()

  def stop(self):
    self._stop_event.set()

  @property
  def running(self):
    return not self._stop_event.is_set()

#
# Symbol worker, will fetch data, turn it into numpy array and then add it
# to saving queue
#
class SymbolWorker (StoppableThread):

  def __init__ (self, i, trader, logger, symbol_queue, saving_queue, *args, **kwargs):
    super(SymbolWorker, self).__init__(*args, **kwargs)
    self.__i = i
    self.__trader = trader
    self.__logger = logger
    self.__symbol_queue = symbol_queue
    self.__saving_queue = saving_queue
  
  def run (self, *args, **kwargs):
    while self.running or not self.__symbol_queue.empty():
      if not self.__symbol_queue.empty():
        symbol = self.__symbol_queue.get()
        self.__logger.debug("Worker #{} got symbol {} from queue".format(self.__i, symbol))
        order_book = self.__trader.getOrderBook (symbol)
        asks = order_book['asks']
        asks.reverse()
        asks = np.array(asks).astype(float)
        bids = order_book['bids']
        bids = np.array(bids).astype(float)
        arr  = np.concatenate((asks, bids))
        mean = (np.min(asks[-1][0]) + np.min(bids[0][0]))/2
        self.__logger.info("Symbol {}: {}".format(symbol, mean))
        self.__saving_queue.put((symbol, arr, mean))
    self.__logger.debug("Worker #{} shutting down...".format(self.__i))
    return True

#
# Saving worker, will get data from queue and save it
#
class SavingWorker (StoppableThread):

  def __init__ (self, i, trader, logger, saving_queue, locks, *args, **kwargs):
    super(SavingWorker, self).__init__(*args, **kwargs)
    self.__i = i
    self.__trader = trader
    self.__logger = logger
    self.__saving_queue = saving_queue
    self.__r = Redis()
    self.__locks = locks

  def npFromRedis (self, key, dims):
    encoded = self.__r.get(key)
    arr = None
    if encoded is None:
      return arr
    if dims == 1:
      a = struct.unpack('>I', encoded[:4])
      arr = np.frombuffer(encoded[4:]).reshape(a)
    elif dims == 2:
      a, b = struct.unpack('>II', encoded[:8])
      arr = np.frombuffer(encoded[8:]).reshape(a, b)
    elif dims == 3:
      a, b, c = struct.unpack('>III', encoded[:12])
      arr = np.frombuffer(encoded[12:]).reshape(a, b, c)
    return arr

  def npToRedis (self, key, arr, dims):
    if dims == 1:
      a = arr.shape[0]
      shape = struct.pack('>I', a)
    elif dims == 2:
      a, b = arr.shape
      shape = struct.pack('>II', a, b)
    elif dims == 3:
      a, b, c = arr.shape
      shape = struct.pack('>III', a, b, c)
    else:
      return False
    encoded = shape + arr.tobytes()
    return self.__r.set(key, encoded)

  def run (self, *args, **kwargs):
    while self.running or not self.__saving_queue.empty:
      if not self.__saving_queue.empty():
        symbol, arr, mean = self.__saving_queue.get()
        self.__logger.debug("Saving worker #{} got symbol {} from queue, acquiring lock...".format(self.__i, symbol))
        self.__locks[symbol].acquire()
        self.__logger.debug("Saving worker #{} ACQUIRED symbol {} lock".format(self.__i, symbol))
        X = self.npFromRedis('X_{}'.format(symbol), 3)
        y = self.npFromRedis('y_{}'.format(symbol), 1)
        if X is None:
          self.__logger.debug("Key for symbol {} did not exist, this is the first time you'll add data to it".format(symbol))
          X = arr.reshape(1, arr.shape[0], arr.shape[1])
          y = np.array([mean])
        else:
          X = np.concatenate((X, arr.reshape(1, arr.shape[0], arr.shape[1])))
          y = np.concatenate((y, [mean]))
        self.__logger.verbose("{}: X {}, y {}".format(symbol, X.shape, y.shape))
        success1 = self.npToRedis('X_{}'.format(symbol), X, 3)
        success2 = self.npToRedis('y_{}'.format(symbol), y, 1)
        if not (success1 and success2):
          self.__logger.error ("Failed to save data to Redis server: X={}, y={}".format(success1, success2))
        self.__locks[symbol].release()
        self.__logger.debug("Saving worker #{} RELEASED symbol {} lock".format(self.__i, symbol))
    self.__logger.debug("Saving worker #{} shutting down...".format(self.__i))
    return True

def timed_requests ():
  if running:
    Timer(1, timed_requests).start()
    for symbol in trader.symbols:
      logger.info("Scheduling symbol {}".format(symbol))
      symbol_queue.put(symbol)

if __name__ == '__main__':

  logger.info ("Clearing Redis keys...")
  r = Redis()
  for symbol in trader.symbols:
    r.delete('X_{}'.format(symbol))
    r.delete('y_{}'.format(symbol))

  logger.info ("Creating locks for symbols...")
  for symbol in trader.symbols:
    locks[symbol] = Lock()

  logger.info ("Starting data collector...")

  workers = []

  logger.info ("Adding symbol workers...")
  for i in range(SYMBOL_WORKERS):
    worker = SymbolWorker(i+1, trader, logger, symbol_queue, saving_queue)
    workers.append(worker)
    worker.setDaemon(True)
    worker.start()
  
  logger.info ("Adding saving workers...")
  for j in range(SAVING_WORKERS):
    worker = SavingWorker(j+1, trader, logger, saving_queue, locks)
    workers.append(worker)
    worker.setDaemon(True)
    worker.start()

  logger.info ("Scheduling first iteration...")
  timed_requests()

  try:
    while True:
      pass
  except KeyboardInterrupt:
    logger.warning("Ctrl+C has been pressed, will finish queues and then shut everything down...")
    running = False
    for worker in workers:
      worker.stop()

