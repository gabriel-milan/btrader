__all__ = [
  'TradingPair'
]

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
      self.__step = None
      for f in symbol['filters']:
        if f['filterType'] == 'LOT_SIZE':
          self.__step = float(f['stepSize'])
      if self.__step == None:
        raise ValueError ("Couldn't get step size for symbol {}".format(self.__symbol))

  @property
  def symbol (self):
    return self.__symbol

  @property
  def step (self):
    return self.__step

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
