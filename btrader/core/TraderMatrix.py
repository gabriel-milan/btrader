__all__ = [
  'TraderMatrix'
]

from time import time
# from btrader.extensions import profit
from btrader.core.TriangularRelationship import TriangularRelationship

class TraderMatrix (dict):

  def __init__ (self, fee=0.1, *args, **kwargs):
    super (TraderMatrix, self).__init__(*args, **kwargs)
    self.__fee = fee/100
  
  def addPair (self, pair: str):
    self[pair] = {}
    self[pair]['asks'] = []
    self[pair]['bids'] = []
    self[pair]['timestamp'] = 0

  def updatePair (self, pair:str, timestamp: float, data: dict):
    if not pair in self.keys():
      self.addPair(pair)
    self[pair]['asks'] = data['asks']
    self[pair]['bids'] = data['bids']
    self[pair]['timestamp'] = timestamp

  def computeRelationship (self, relationship: TriangularRelationship, qtys: list):
    timestamp = 0
    tradingPrices = []
    tradingOperations = []
    for symbol, asks_bids in relationship.workflow:
      if asks_bids == 'bids':
        tradingOperations.append(True)
      else:
        tradingOperations.append(False)
      tradingPrices.append(self[symbol][asks_bids])
      temp_ts = self[symbol]['timestamp']
      if temp_ts >= timestamp:
        timestamp = temp_ts
    # return profit(tradingPrices, tradingOperations, qtys), time()-timestamp