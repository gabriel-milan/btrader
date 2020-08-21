__all__ = [
  'ComputeWorker'
]

import logging
from time import time
from btrader.core.Logger import Logger
from btrader.core.StoppableThread import StoppableThread

class ComputeWorker (StoppableThread):

  def __init__ (self, trader_matrix, trader_lock, queue, queue_lock, config, level=logging.DEBUG, log_file=None, *args, **kwargs):
    super (ComputeWorker, self).__init__(*args, **kwargs)
    self.__logger           = Logger(name="ComputeWorker", level=level, filename=log_file)
    self.__traderMatrix     = trader_matrix
    self.__traderLock       = trader_lock
    self.__queue            = queue
    self.__queueLock        = queue_lock
    self.__config           = config
    self.__ageThreshold     = self.__config["TRADING"]["AGE_THRESHOLD"] / 1000
    self.__profitThreshold  = self.__config["TRADING"]["PROFIT_THRESHOLD"] / 100

  @property
  def logger (self):
    return self.__logger

  def run (self, *args, **kwargs):
    while self.running:
      self.__queueLock.acquire()
      if not self.__queue.empty():
        rel = self.__queue.get()
        self.__queueLock.release()
        self.__traderLock.acquire()
        qty, profit, timestamp = self.__traderMatrix.computeRelationship(rel.text)
        self.__traderLock.release()
        if ((time()-timestamp) <= self.__ageThreshold) and (profit >= self.__profitThreshold):
          self.logger.debug("{} \t (age: {}s): \t {:.4f}%".format(rel.text, time()-timestamp, profit*100))
        self.__queue.put(rel)
      else:
        self.__queueLock.release()
    self.logger.debug("Shutting down...")
    self.logger.shutdown()
    return True