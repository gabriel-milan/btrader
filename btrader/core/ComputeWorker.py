__all__ = [
  'ComputeWorker'
]

import logging
from time import time
from binance.exceptions import *
from btrader.core.Logger import Logger
from btrader.core.StoppableThread import StoppableThread

class ComputeWorker (StoppableThread):

  def __init__ (self, trader_matrix, trader_lock, queue, queue_lock, config, trading_lock, trading_queue, client, counter, stepDict, telegramBot=None, level=logging.DEBUG, log_file=None, *args, **kwargs):
    super (ComputeWorker, self).__init__(*args, **kwargs)
    self.__logger           = Logger(name="ComputeWorker", level=level, filename=log_file)
    self.__traderMatrix     = trader_matrix
    self.__traderLock       = trader_lock
    self.__queue            = queue
    self.__queueLock        = queue_lock
    self.__config           = config
    self.__ageThreshold     = self.__config["TRADING"]["AGE_THRESHOLD"] / 1000
    self.__profitThreshold  = self.__config["TRADING"]["PROFIT_THRESHOLD"] / 100
    self.__tradingEnabled   = self.__config["TRADING"]["ENABLED"]
    self.__tradingQueue     = trading_queue
    self.__tradingLock      = trading_lock
    self.__client           = client
    self.counter            = counter
    self.maxCount           = self.__config["TRADING"]["EXECUTION_CAP"] if self.__config["TRADING"]["EXECUTION_CAP"] > 0 else float('inf')
    self.__stepDict         = stepDict
    self.__telegramBot      = telegramBot

  @property
  def tradingEnabled (self):
    return (self.__tradingEnabled and (self.counter.value < self.maxCount))

  @property
  def logger (self):
    return self.__logger

  @property
  def client (self):
    return self.__client
  
  @property
  def telegramBot (self):
    return self.__telegramBot

  def correctQuantity (self, quantity, symbol):
    step = self.__stepDict[symbol]
    return round (quantity, -int(f'{step:e}'.split('e')[-1]))

  def run (self, *args, **kwargs):
    while self.running:
      self.__queueLock.acquire()
      if not self.__queue.empty():
        rel = self.__queue.get()
        self.__queueLock.release()
        self.__traderLock.acquire()
        deal = self.__traderMatrix.computeRelationship(rel.text)
        profit = deal.getProfit()
        timestamp = deal.getTimestamp()
        self.__traderLock.release()
        age = (time()-timestamp)
        age_ms = age*1000

        if (age <= self.__ageThreshold) and (profit >= self.__profitThreshold):
          self.logger.debug("{} \t (age: {:.2f}ms): \t {:.4f}%".format(rel.text, age_ms, profit*100))

          # TODO: Think of a better way of managing this lock.
          # Can trigger multiple times with the same triangle
          # if deal still worth it for couple seconds. Should
          # this be a thing? Or should I execute this trade
          # and then forget about it for a while?

          self.__tradingLock.acquire()
          if self.tradingEnabled:
            self.executeDeal(deal)
            with self.counter.get_lock():
              self.counter.value += 1
          else:
            self.logger.debug("Trading disabled (either by configuration or max count reached)")
            self.printDeal(deal)
            self.telegramBot.sendMessage("Trading disabled (either by configuration or max count reached)")
          self.__tradingLock.release()

          if self.telegramBot is not None:
            self.telegramBot.sendDeal(deal, age_ms)

        self.__traderLock.acquire()
        self.__traderMatrix.addAge(age_ms)
        self.__traderLock.release()

        self.__queue.put(rel)
      else:
        self.__queueLock.release()
    self.logger.shutdown()
    return True

  def printDeal (self, deal):
    self.logger.info("--> Printing trading steps")
    for action in deal.getActions():
      self.logger.info ("{} {} from pair {}".format(
        action.getAction(),
        self.correctQuantity(action.getQuantity(), action.getPair()),
        action.getPair(),
      ))
    self.logger.info("--------------------------")

  def executeDeal (self, deal):
    self.logger.debug("--> Executing deal")
    for i, action in enumerate(deal.getActions()):

      # Get deal data
      buy_sell = action.getAction()
      pair = action.getPair()
      qty = self.correctQuantity(action.getQuantity(), pair)

      # If action is buying
      if buy_sell == "BUY":
        try:
          self.logger.info ("#{}: Buying {} from symbol {}".format(i+1, qty, pair))
          order = self.client.order_market_buy(symbol=pair, quantity=qty)
        except Exception as e:
          self.logger.error("Failed to execute action #{} (symbol={}, qty={})".format(i+1, pair, qty))
          raise e

      # If action is selling
      elif buy_sell == "SELL":
        try:
          self.logger.info ("#{}: Selling {} from symbol {}".format(i+1, qty, pair))
          order = self.client.order_market_sell(symbol=pair, quantity=qty)
        except Exception as e:
          self.logger.error("Failed to execute action #{} (symbol={}, qty={})".format(i+1, pair, qty))
          raise e

      # If something's messed up
      else:
        self.logger.error("Unknown operation {}".format(buy_sell))
        raise ValueError ("Unknown operation {}".format(buy_sell))

      # Order checking before moving to next action
      self.logger.debug (order)
      status = None
      while (status is None):
        try:
          status = self.client.get_order(symbol=pair, orderId=order['orderId'])
        except BinanceAPIException:
          self.logger.debug("Couldn't find order yet, retrying...")
      self.logger.debug (status)
      while (status['status'] != 'FILLED'):
        status = self.client.get_order(symbol=pair, orderId=order['orderId'])
        self.logger.debug (status)
    self.logger.info("--------------------------")
