__all__ = [
  'DepthWorker'
]

import logging
from time import time
from btrader.core.Logger import Logger
from btrader.core.StoppableThread import StoppableThread

class DepthWorker (StoppableThread):

  def __init__ (self, trader_matrix, trader_lock, queue_lock, queue, level=logging.DEBUG, log_file=None, *args, **kwargs):
    super(DepthWorker, self).__init__(*args, **kwargs)
    self.__logger       = Logger(name="DepthWorker", level=level, filename=log_file)
    self.__traderMatrix = trader_matrix
    self.__traderLock   = trader_lock
    self.__queueLock    = queue_lock
    self.__queue        = queue

  @property
  def logger (self):
    return self.__logger

  def process (self, queue, *args, **kwargs):
    while self.running:
      self.__queueLock.acquire()
      if not queue.empty():
        symbol, timestamp, data = queue.get()
        self.__queueLock.release()
        # self.logger.debug("Updating symbol {} with {}s delay".format(symbol, time()-timestamp))
        self.__traderLock.acquire()
        self.__traderMatrix.updatePair(symbol, timestamp, data['asks'], data['bids'])
        self.__traderLock.release()
      else:
        self.__queueLock.release()
    self.logger.shutdown()
    return True

  def run (self):
    return self.process(self.__queue)