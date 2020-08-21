__all__ = [
  'ComputeWorker'
]

import json
import logging
from time import time
from redis import Redis
from btrader.core.Logger import Logger

class ComputeWorker ():

  def __init__ (self, trader_matrix, level=logging.DEBUG, log_file=None, *args, **kwargs):
    super (ComputeWorker, self).__init__(*args, **kwargs)
    self.__logger         = Logger(name="ComputeWorker", level=level, filename=log_file)
    self.__traderMatrix   = trader_matrix

  @property
  def logger (self):
    return self.__logger

  def parse_data (self, inp):
    if inp is not None:
      inp = inp.decode()
      split = inp.split('@')
      timestamp = float(split[0])
      data = json.loads('@'.join(split[1:]).replace("'", "\""))
      return timestamp, data
    return None, None

  def process (self, relationships, *args, **kwargs):
    while True:
      rel = relationships[0]
      qty, profit, timestamp = self.__traderMatrix.computeRelationship(rel.text)
      # self.logger.debug("{} (delay {}s): {}".format(rel.text, time()-timestamp, profit))
    self.logger.debug("Shutting down...")
    self.logger.shutdown()
    return True