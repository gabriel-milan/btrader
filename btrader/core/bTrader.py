__all__ = [
  'bTrader'
]

import sys
import json
import timeit
import logging
import numpy as np
from queue import Queue
import concurrent.futures
from threading import Lock
from atexit import register
from time import time, sleep
from functools import partial
from binance.client import Client
from multiprocessing import Value
from btrader.core.Logger import Logger
from btrader.extensions import TraderMatrix, Deal
from btrader.bot.TelegramBot import TelegramBot
from btrader.core.DepthWorker import DepthWorker
from btrader.core.TradingPair import TradingPair
from binance.websockets import BinanceSocketManager
from btrader.core.ComputeWorker import ComputeWorker
from btrader.core.StoppableThread import StoppableThread
from btrader.core.TriangularRelationship import TriangularRelationship

SOCKET_WORKERS  = 8
DEPTH_WORKERS   = 2
COMPUTE_WORKERS = 6
TRADE_WORKERS   = 0

class bTrader (StoppableThread):

  def __init__ (self, config_path, level=logging.DEBUG, log_file=None, *args, **kwargs):

    # Initial values (don't get lost on class attributes)
    self.__logger             = None  # Logger
    self.__logFile            = ""    # Log file path
    self.__level              = None  # logging level
    self.__config             = {}    # A dict from JSON input file
    self.__apiKey             = ""    # API key (from self.__config)
    self.__apiSecret          = ""    # API secret (from self.__config)
    self.__client             = None  # Client
    self.__info               = {}    # Got from Binance API
    self.__symbols            = []    # List of TradingPair (all of them)
    self.__stepDict           = {}    # Dict of steps of all symbols (all of them)
    self.__base               = ""    # Base coin (from self.__config)
    self.__relationships      = []    # List of TriangularRelationship
    self.__relationshipLock   = None  # Lock for the relationship queue
    self.__relationshipQueue  = None  # Queue for relationships
    self.__sockets            = []    # List of TradingPair (the ones we'll use)
    self.__socketWorkers      = None  # concurrent.futures.ThreadPoolExecutor
    self.__socketManagers     = []    # List of BinanceSocketManager
    self.__depthQueue         = None  # Queue
    self.__depthLock          = None  # Queue Lock
    self.__depthWorkers       = []    # List of DepthWorker
    self.__computeWorkers     = []    # List of ComputeWorker
    self.__traderMatrix       = None  # Main trading matrix
    self.__traderLock         = None  # Lock for TradingMatrix
    self.__tradingQueue       = None  # Queue for trade
    self.__tradingLock        = None  # Lock for trade
    self.__tradingCount       = None  # mp.Value used to hold number of deals executed

    # Init super
    super(bTrader, self).__init__(*args, **kwargs)

    # Logger
    self.__logFile  = log_file
    self.__level    = level
    self.__logger   = Logger(name="bTrader", level=level, filename=log_file)

    # Loading configuration
    with open (config_path, 'r') as cf:
      jt = cf.read()
      jd = json.loads(jt)
    self.__config = jd

    # Trading matrix
    self.__traderMatrix = TraderMatrix(
      self.__config['TRADING']['TAKER_FEE'],
      np.arange(
        self.__config['INVESTMENT']['MIN'],
        self.__config['INVESTMENT']['MAX'],
        self.__config['INVESTMENT']['STEP'],
      )
    )
    self.__traderLock = Lock()

    # Trying to configure Telegram Bot
    if 'TELEGRAM' not in self.__config:
      self.logger.info("Telegram configuration is not available at configuration file, skipping...")
      self.__telegramBot = None
    else:
      try:
        self.__telegramBot = TelegramBot(
          token=self.__config['TELEGRAM']['TOKEN'],
          user_id=self.__config['TELEGRAM']['USER_ID'],
          level=level,
          log_file=log_file,
          trader_matrix=self.__traderMatrix,
        )
        self.__telegramBot.start()
      except Exception as e:
        self.logger.error("Failed to setup Telegram Bot")
        raise e

  @property
  def info (self):
    return self.__info

  @property
  def systemStatus (self):
    return self.__client.get_system_status()

  @property
  def logger (self):
    return self.__logger

  @property
  def telegramBot (self):
    return self.__telegramBot

  def initialize(self):
    # Connecting to Binance
    self.logger.info("Starting Binance API client...")
    self.__apiKey = self.__config['KEYS']['API']
    self.__apiSecret = self.__config['KEYS']['SECRET']
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
      for pair in self.__symbols:
        self.__stepDict[pair.symbol] = pair.step
      self.logger.info("Found {} market pairs".format(len(self.__symbols)))
    except Exception as e:
      self.logger.critical("Failed to get market pairs")
      raise e

    # Getting triangular relationships
    try:
      self.__relationshipQueue = Queue()
      self.__relationshipLock = Lock()
      self.__base = self.__config['INVESTMENT']['BASE']
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
                self.__traderLock.acquire()
                self.__traderMatrix.createPair(
                  start_pair.symbol,
                  start_pair.step,
                )
                self.__traderLock.release()
              if not end_pair in self.__sockets:
                self.__sockets.append(end_pair)
                self.__traderLock.acquire()
                self.__traderMatrix.createPair(
                  end_pair.symbol,
                  end_pair.step,
                )
                self.__traderLock.release()
              self.__sockets.append(middle_pair)
              self.__traderLock.acquire()
              self.__traderMatrix.createPair(
                middle_pair.symbol,
                middle_pair.step,
              )
              self.__traderLock.release()
              self.__relationships.append(TriangularRelationship(self.__base, start_pair, middle_pair, end_pair))
              self.__relationships.append(TriangularRelationship(self.__base, end_pair, middle_pair, start_pair))
      self.logger.info("Found {} triangular relationships".format(len(self.__relationships)))
      self.logger.debug("Will need to open {} sockets for depth acquiring".format(len(self.__sockets)))
    except Exception as e:
      self.logger.critical("Failed to get triangular relationships")
      raise e

    self.logger.info("Setup complete")

  def __socketCallback (self, symbol, data):
    if data is not None:
      timestamp = time()
      # self.logger.debug("Putting pair {}".format(symbol))
      self.__depthQueue.put((symbol, timestamp, data))
    else:
      self.logger.error("Failed to get depth data for pair {}".format(symbol))

  def __setupSocketManager(self, i):
    self.__socketManagers[i].start_depth_socket(
      self.__sockets[i].symbol,
      partial(self.__socketWorkers.submit, partial(self.__socketCallback, self.__sockets[i].symbol)),
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

  def execute(self):

    self.__tradingQueue = Queue()
    self.__tradingLock = Lock()

    self.logger.debug("Constructing socket managers...")
    self.__socketWorkers = concurrent.futures.ThreadPoolExecutor(max_workers=SOCKET_WORKERS)
    self.__socketManagers = [BinanceSocketManager(self.__client) for sock in self.__sockets]

    self.logger.info("Starting {} depth worker(s)...".format(DEPTH_WORKERS))
    self.__depthQueue     = Queue()
    self.__depthLock      = Lock()
    for i in range(DEPTH_WORKERS):
      worker = DepthWorker(
        level=self.__level,
        log_file=self.__logFile,
        trader_matrix=self.__traderMatrix,
        trader_lock=self.__traderLock,
        queue=self.__depthQueue,
        queue_lock=self.__depthLock
      )
      worker.setDaemon(True)
      worker.start()
      self.__depthWorkers.append(worker)

    self.logger.debug("Setting up depth sockets and callbacks with {} socket workers...".format(SOCKET_WORKERS))
    cachePromises  = []
    for i in range(len(self.__sockets)):
      cachePromises.append(self.__socketWorkers.submit(self.__setupSocketManager, i))
    while not self.__promisesCompleted(cachePromises):
      self.logger.info("Waiting on sockets to be up")
      from time import sleep
      sleep(1)
    self.logger.info("Sockets and cache all set up.")

    self.logger.debug("Setting up triangular relationships")
    for relationship in self.__relationships:
      self.__traderLock.acquire()
      self.__traderMatrix.createRelationship(relationship.text, relationship.pairs, relationship.actions)
      self.__traderLock.release()
      self.__relationshipQueue.put(relationship)

    self.logger.info("Starting {} compute worker(s)...".format(COMPUTE_WORKERS))
    self.__tradingCount = Value('i')
    for i in range(COMPUTE_WORKERS):
      worker = ComputeWorker(
        level=self.__level,
        log_file=self.__logFile,
        trader_matrix=self.__traderMatrix,
        trader_lock=self.__traderLock,
        queue=self.__relationshipQueue,
        queue_lock=self.__relationshipLock,
        config=self.__config,
        trading_lock=self.__tradingLock,
        trading_queue=self.__tradingQueue,
        client=self.__client,
        counter=self.__tradingCount,
        stepDict=self.__stepDict,
        telegramBot=self.telegramBot,
      )
      worker.setDaemon(True)
      worker.start()
      self.__computeWorkers.append(worker)

    self.logger.info("Initialization done, will work now")

  def finalize(self):
    try:
      self.logger.warning("Shutting down shouldn't take more than 10s but, if it does, please pless Ctrl+C again...")
      # Stop SocketManagers
      self.logger.info("Stopping socket managers...")
      for sm in self.__socketManagers:
        sm.close()
      # Stop SocketWorkers
      self.__socketWorkers.shutdown()
      # Stopping Depth workers
      self.logger.info("Stopping depth workers...")
      for worker in self.__depthWorkers:
        worker.stop()
      # Stopping Compute workers
      self.logger.info("Stopping compute workers...")
      for worker in self.__computeWorkers:
        worker.stop()
      # Stop Logger
      self.logger.shutdown()
      # Stop main thread
      self.logger.info("Exiting...")
      self.stop()
    except Exception as e:
      self.logger.error("Error shutting everything down. Doing it anyway =)")
    finally:
      sys.exit(0)

  def run (self, *args, **kwargs):
    register(self.finalize)
    try:
      self.initialize()
      self.execute()
    except KeyboardInterrupt:
      return
    except Exception as e:
      self.logger.critical("Unknown error, please report.")
      raise e
