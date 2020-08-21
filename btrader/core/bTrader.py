__all__ = [
  'bTrader'
]

import json
import timeit
import logging
import numpy as np
from tqdm import tqdm
from redis import Redis
import concurrent.futures
from time import time, sleep
from functools import partial
from binance.client import Client
from btrader.core.Logger import Logger
from multiprocessing import Queue, Pool
from btrader.extensions import ClassWithNoName
from btrader.core.DepthWorker import DepthWorker
from btrader.core.TradingPair import TradingPair
from btrader.core.TraderMatrix import TraderMatrix
from binance.websockets import BinanceSocketManager
from btrader.core.ComputeWorker import ComputeWorker
from btrader.core.StoppableThread import StoppableThread
from btrader.core.TriangularRelationship import TriangularRelationship

SOCKET_WORKERS  = 6
DEPTH_WORKERS   = 8
COMPUTE_WORKERS = 2

class bTrader (StoppableThread):

  def __init__ (self, config_path, level=logging.DEBUG, log_file=None, *args, **kwargs):

    # Initial values (don't get lost on class attributes)
    self.__logger         = None  # Logger
    self.__logFile        = ""    # Log file path
    self.__level          = None  # logging level
    self.__config         = {}    # A dict from JSON input file
    self.__apiKey         = ""    # API key (from self.__config)
    self.__apiSecret      = ""    # API secret (from self.__config)
    self.__client         = None  # Client
    self.__info           = {}    # Got from Binance API
    self.__symbols        = []    # List of TradingPair (all of them)
    self.__base           = ""    # Base coin (from self.__config)
    self.__relationships  = []    # List of TriangularRelationship
    self.__sockets        = []    # List of TradingPair (the ones we'll use)
    self.__socketWorkers  = None  # concurrent.futures.ThreadPoolExecutor
    self.__depthQueue     = None  # Queue
    self.__socketManagers = []    # List of BinanceSocketManager
    self.__depthPool      = None  # Pool of DepthWorker
    self.__computePool    = None  # Pool of ComputeWorker
    self.__r              = None  # Redis instance
    self.__traderMatrix   = None  # Main trading matrix

    # Init super
    super(bTrader, self).__init__(*args, **kwargs)

    # Logger
    self.__logFile  = log_file
    self.__level    = level
    self.__logger   = Logger(name="bTrader", level=level, filename=log_file)

    # Redis
    self.__r = Redis()

    # Loading configuration
    with open (config_path, 'r') as cf:
      jt = cf.read()
      jd = json.loads(jt)
    self.__config = jd

    # Trading matrix
    self.__traderMatrix = ClassWithNoName(
      self.__config['TRADING']['TAKER_FEE'],
      np.arange(
        self.__config['INVESTMENT']['MIN'],
        self.__config['INVESTMENT']['MAX'],
        self.__config['INVESTMENT']['STEP'],
      )
    )

  def initialize (self):

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
      self.logger.info("Found {} market pairs".format(len(self.__symbols)))
    except Exception as e:
      self.logger.critical("Failed to get market pairs")
      raise e

    # Getting triangular relationships
    try:
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
                self.__traderMatrix.createPair(start_pair.symbol)
              if not end_pair in self.__sockets:
                self.__sockets.append(end_pair)
                self.__traderMatrix.createPair(end_pair.symbol)
              self.__sockets.append(middle_pair)
              self.__traderMatrix.createPair(middle_pair.symbol)
              self.__relationships.append(TriangularRelationship(self.__base, start_pair, middle_pair, end_pair))
              self.__relationships.append(TriangularRelationship(self.__base, end_pair, middle_pair, start_pair))
      self.logger.info("Found {} triangular relationships".format(len(self.__relationships)))
      self.logger.debug("Will need to open {} sockets for depth acquiring".format(len(self.__sockets)))
      self.__socketWorkers = concurrent.futures.ThreadPoolExecutor(max_workers=SOCKET_WORKERS)
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
      timestamp = time()
      self.__depthQueue.put((symbol, timestamp, data))
    else:
      self.logger.error("Failed to get depth data for pair {}".format(symbol))

  def __setupBM(self, i):
    self.__socketManagers[i].start_depth_socket(
      self.__sockets[i].symbol,
      partial(self.__socketWorkers.submit, partial(self.__depth_callback, self.__sockets[i].symbol)),
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

    self.logger.debug("Clearing Redis cache...")
    for sock in self.__sockets:
      self.__r.delete(sock.symbol)

    self.logger.debug("Constructing socket managers...")
    self.__socketManagers = [BinanceSocketManager(self.__client) for sock in self.__sockets]

    self.logger.info("Starting pool with {} depth worker(s)...".format(DEPTH_WORKERS))
    self.__depthQueue     = Queue()
    worker = DepthWorker(level=self.__level, log_file=self.__logFile, trader_matrix=self.__traderMatrix)
    self.__depthPool = Pool(DEPTH_WORKERS, worker.process, (self.__depthQueue,))

    self.logger.debug("Setting up depth sockets...")
    cachePromises  = []
    for i in range(len(self.__sockets)):
      cachePromises.append(self.__socketWorkers.submit(self.__setupBM, i))
    while not self.__promisesCompleted(cachePromises):
      self.logger.info("Waiting on sockets to be up")
      from time import sleep
      sleep(1)
    self.logger.info("Sockets and cache all set up.")

    self.logger.info("Starting pool with {} compute worker(s)...".format(COMPUTE_WORKERS))
    worker = ComputeWorker(trader_matrix=self.__traderMatrix, level=self.__level, log_file=self.__logFile)
    for relationship in self.__relationships:
      self.__traderMatrix.createRelationship(relationship.text, relationship.pairs, relationship.actions)
    self.__computePool = Pool(COMPUTE_WORKERS, worker.process, (self.__relationships,))

  def run (self, *args, **kwargs):
    self.initialize()
    self.getWebsockets()
    try:
      while self.running:
        pass
    except KeyboardInterrupt:
      self.logger.warning("Ctrl+C has been pressed, shutting down shouldn't take more than 10s but, if it does, please pless Ctrl+C again...")
      # Stop SocketManagers
      for sm in self.__socketManagers:
        sm.close()
      sleep(1)
      # Stop SocketWorkers
      self.__socketWorkers.shutdown()
      # Stop Pools
      self.__depthPool.terminate()
      self.__computePool.terminate()
      # Stop Logger
      self.logger.shutdown()
      # Stop main thread
      self.stop()