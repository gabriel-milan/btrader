__all__ = [
  'bTrader'
]

import json
import timeit
import logging
from tqdm import tqdm
import concurrent.futures
from functools import partial
from binance.client import Client
from btrader.core.Logger import Logger
from binance.websockets import BinanceSocketManager

class bTrader ():

  def __init__ (self, config_path, level=logging.DEBUG):

    self.__logger = Logger(name="bTrader", level=level)

    # Loading configuration
    self.logger.info("Loading configuration file...")
    with open (config_path, 'r') as cf:
      jt = cf.read()
      jd = json.loads(jt)
    self.__config = jd

    # Connecting to Binance
    self.logger.info("Starting Binance API client...")
    self.__apiKey = jd['KEYS']['API']
    self.__apiSecret = jd['KEYS']['SECRET']
    try:
      self.__client = Client(self.__apiKey, self.__apiSecret)
      assert self.__client.ping() == {}
      ms = timeit.timeit(self.__client.ping, number=10)*100
      self.logger.info("Successfully connected to Binance with {:.2f}ms of mean latency".format(ms))
    except Exception as e:
      self.logger.critical("Exception occured on setting up client:")
      raise e

    # Listing trading pairs
    try:
      self.__info = self.__client.get_exchange_info()
      self.__symbols = [TradingPair(s) for s in self.__info['symbols'] if s['status'] == 'TRADING']
      self.logger.info("Found {} market pairs".format(len(self.__symbols)))
    except Exception as e:
      self.logger.critical("Failed to get market pairs")
      raise e

    # Getting triangular relationships
    try:
      self.__base = self.__config['INVESTMENT']['BASE']
      self.__relationships = []
      self.__sockets = []
      starters = [ x for x in self.__symbols if x.hasAsset(self.__base) ]
      self.logger.debug("Found {} start/end market pairs".format(len(starters)))
      for i, start_pair in enumerate(starters[:-1]):
        for j, end_pair in enumerate(starters[i+1:]):
          middle = TradingPair(None, start_pair.getTheOther(self.__base), end_pair.getTheOther(self.__base))
          for middle_pair in self.__symbols:
            if middle == middle_pair:
              if not start_pair in self.__sockets:
                self.__sockets.append(start_pair)
              if not end_pair in self.__sockets:
                self.__sockets.append(end_pair)
              self.__sockets.append(middle_pair)
              self.__relationships.append(TriangularRelationship(self.__base, start_pair, middle_pair, end_pair))
              self.__relationships.append(TriangularRelationship(self.__base, end_pair, middle_pair, start_pair))
      self.logger.info("Found {} triangular relationships".format(len(self.__relationships)))
      self.logger.debug("Will need to open {} sockets for depth acquiring".format(len(self.__sockets)))
      self.__socketOpener = concurrent.futures.ThreadPoolExecutor(max_workers=len(self.__sockets))
    except Exception as e:
      self.logger.critical("Failed to get triangular relationships")
      raise e

    self.logger.info("Setup completed successfully!")

  @property
  def info (self):
    return self.__info

  @property
  def systemStatus (self):
    return self.__client.get_system_status()

  @property
  def logger (self):
    return self.__logger

  def __depth_callback (self, symbol, data):
    if data is not None:
      print(symbol, data)
    else:
      self.logger.error("Failed to get depth data")

  def __setupBM(self, i):
    self.__socketManagers[i].start_depth_socket(
      self.__sockets[i].symbol,
      partial(self.__depth_callback, self.__sockets[i].symbol),
      depth=self.__config['DEPTH']['SIZE']
    )
    self.__socketManagers[i].start()

  def __promisesCompleted (self, promises):
    completed = True
    for promise in promises:
      if promise.running():
        completed = False
        return completed
    return completed

  def getWebsockets (self):
    self.logger.debug("Constructing socket managers...")
    self.__socketManagers = [BinanceSocketManager(self.__client) for sock in self.__sockets]
    self.logger.debug("Setting up depth sockets...")
    cachePromises  = []
    for i in range(len(self.__sockets)):
      cachePromises.append(self.__socketOpener.submit(self.__setupBM, i))
    while not self.__promisesCompleted(cachePromises):
      self.logger.info("Waiting on sockets to be up")
      from time import sleep
      sleep(1)
    self.logger.info("Sockets and cache all set up.")

  def loop (self):
    try:
      while True:
        pass
    except KeyboardInterrupt:
      self.logger.warning("Ctrl+C has been pressed, shutting everything down now...")
      promises = []
      for sm in self.__socketManagers:
        promises.append(sm.close())
      while not self.__promisesCompleted(promises):
        pass
      self.logger.warning("Exited gently.")

class TradingPair ():

  def __init__ (self, symbol, base=None, quote=None):
    if not symbol:
      self.__symbol = base+quote
      self.__baseAsset = base
      self.__quoteAsset = quote
    else:
      self.__symbol = symbol['symbol']
      self.__baseAsset = symbol['baseAsset']
      self.__baseAssetPrecision = symbol['baseAssetPrecision']
      self.__quoteAsset = symbol['quoteAsset']
      self.__quoteAssetPrecision = symbol['quoteAssetPrecision']

  @property
  def symbol (self):
    return self.__symbol

  @property
  def baseAsset (self):
    return self.__baseAsset

  @property
  def baseAssetPrecision (self):
    return self.__baseAssetPrecision

  @property
  def quoteAsset (self):
    return self.__quoteAsset

  @property
  def quoteAssetPrecision (self):
    return self.__quoteAssetPrecision

  def hasAsset (self, asset):
    if self.quoteAsset == asset or self.baseAsset == asset:
      return True
    return False

  def getTheOther (self, asset):
    if self.quoteAsset == asset:
      return self.baseAsset
    elif self.baseAsset == asset:
      return self.quoteAsset
    else:
      return None

  def __repr__ (self):
    return ("<TradingPair {}/{}>".format(self.baseAsset, self.quoteAsset))

  def __str__ (self):
    return self.__repr__()

  @property
  def text (self):
    return "{}/{}".format(self.baseAsset, self.quoteAsset)

  def __eq__ (self, tp):
    if ((tp.quoteAsset == self.quoteAsset) and (tp.baseAsset == self.baseAsset)) or ((tp.quoteAsset == self.baseAsset) and (tp.baseAsset == self.quoteAsset)):
      return True
    return False

class TriangularRelationship ():

  def __init__ (self, base, start_pair, middle_pair, end_pair):
    self.__base = base
    self.__start = start_pair
    self.__middle = middle_pair
    self.__end = end_pair
    self.__actions = []
    self.__intermediates = []

    # Base -> Middle
    if self.__base == self.__start.baseAsset:
      self.__actions.append('SELL')
      nextBase = self.__start.quoteAsset
    else:
      self.__actions.append('BUY')
      nextBase = self.__start.baseAsset

    self.__intermediates.append(nextBase)

    # Middle -> End
    if nextBase == self.__middle.baseAsset:
      self.__actions.append('SELL')
      nextBase = self.__middle.quoteAsset
    else:
      self.__actions.append('BUY')
      nextBase = self.__middle.baseAsset

    self.__intermediates.append(nextBase)

    # End -> Base
    if nextBase == self.__end.baseAsset:
      self.__actions.append('SELL')
    else:
      self.__actions.append('BUY')
  
  def describe(self):
    return "{} from {}, then {} from {} and finally {} from {}".format(
      self.__actions[0], self.__start.text,
      self.__actions[1], self.__middle.text,
      self.__actions[2], self.__end.text
    )
  
  @property
  def text (self):
    return "{} -> {} -> {}".format(self.__base, self.__intermediates[0], self.__intermediates[1])