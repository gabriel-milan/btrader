__all__ = [
  'TradeWorker'
]

import logging
from btrader.core.Logger import Logger
from btrader.core.StoppableThread import StoppableThread

class TradeWorker (StoppableThread):

  def __init__ (self, client, btrader, trading_lock, trading_queue, level=logging.DEBUG, log_file=None, *args, **kwargs):
    super(TradeWorker, self).__init__(*args, **kwargs)
    self.__logger         = Logger(name="TradeWorker", level=level, filename=log_file)
    self.__client         = client
    self.__btrader        = btrader
    self.__tradingLock    = trading_lock
    self.__tradingQueue   = trading_queue

  @property
  def client (self):
    return self.__client

  @property
  def trader (self):
    return self.__btrader
  
  @property
  def logger (self):
    return self.__logger

  def execute (self, deal):
    # TODO: Implement here
    self.printDeal(deal)
    pass

  def run (self):
    while self.running:
      pass
      # self.logger.info("A")
      # if not self.__tradingQueue.empty():
      #   deal = self.__tradingQueue.get()
      #   self.execute(deal)
        # self.kill()

  def printDeal (self, deal):
    self.logger.info("--------------------")
    for action in deal.getActions():
      self.logger.info ("{} {} from pair {}".format(
        action.getAction(),
        action.getQuantity(),
        action.getPair(),
      ))

  def kill (self):
    return self.trader.finalize()