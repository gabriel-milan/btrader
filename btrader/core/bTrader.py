__all__ = [
  'bTrader'
]

import json
from tqdm import tqdm
from binance.client import Client

class bTrader ():

  def __init__ (self, config_path):
    with open (config_path, 'r') as cf:
      jt = cf.read()
      jd = json.loads(jt)
    self.__apiKey = jd['credentials']['apiKey']
    self.__apiSecret = jd['credentials']['apiSecret']
    try:
      self.__client = Client(self.__apiKey, self.__apiSecret)
      assert self.__client.ping() == {}
    except:
      print ("FAILED")
    self.__symbols = jd['symbols']

  @property
  def systemStatus (self):
    return self.__client.get_system_status()

  @property
  def symbols (self):
    return self.__symbols

  def getOrderBook (self, symbol):
    if symbol not in self.__symbols:
      return False
    return self.__client.get_order_book(symbol=symbol)

  def getCandles (self, symbol, interval=Client.KLINE_INTERVAL_30MINUTE):
    if symbol not in self.__symbols:
      return False
    return self.__client.get_klines(symbol=symbol, interval=interval)

  def getHistoricalCandles (self, symbol, interval=Client.KLINE_INTERVAL_1MINUTE, range_start="1 day ago UTC", range_end=None):
    if symbol not in self.__symbols:
      return False
    if range_end:
      return self.__client.get_historical_klines(symbol, interval, range_start, range_end)
    else:
      return self.__client.get_historical_klines(symbol, interval, range_start)

  def getVolume (self, symbol):
    if symbol not in self.__symbols:
      return False
    try:
      return self.__client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, "1 day ago UTC")[0][5]
    except:
      print ("Failed to fetch data for symbol {}".format(symbol))
      return -1

  def getHighestVolumes (self):
    x = {}
    for symbol in tqdm(self.__symbols):
      x[symbol] = self.getVolume(symbol)
    return {k: float(v) for k, v in sorted(x.items(), key=lambda item: -float(item[1]))}