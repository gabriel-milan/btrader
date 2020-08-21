__all__ = [
  'DepthWorker'
]

import logging
from redis import Redis
from btrader.core.Logger import Logger

class DepthWorker ():

  def __init__ (self, trader_matrix, level=logging.DEBUG, log_file=None, *args, **kwargs):
    self.__logger       = Logger(name="DepthWorker", level=level, filename=log_file)
    self.__traderMatrix = trader_matrix

  @property
  def logger (self):
    return self.__logger

  def process (self, queue, *args, **kwargs):
    while True:
      if not queue.empty():
        symbol, timestamp, data = queue.get()
        print (type(data['asks']), data['asks'])
        # self.__traderMatrix.updatePair(symbol, timestamp, data['asks'], data['bids'])
    self.logger.debug("Shutting down...")
    self.logger.shutdown()
    return True