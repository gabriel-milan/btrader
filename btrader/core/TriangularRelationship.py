__all__ = [
  'TriangularRelationship'
]

class TriangularRelationship ():

  def __init__ (self, base, start_pair, middle_pair, end_pair):
    self.__base = base
    self.__start = start_pair
    self.__middle = middle_pair
    self.__end = end_pair
    self.__actions = []
    self.__actionWrappers = []
    self.__intermediates = []

    # Base -> Middle
    if self.__base == self.__start.baseAsset:
      self.__actions.append('SELL')
      self.__actionWrappers.append('bids')
      nextBase = self.__start.quoteAsset
    else:
      self.__actions.append('BUY')
      self.__actionWrappers.append('asks')
      nextBase = self.__start.baseAsset

    self.__intermediates.append(nextBase)

    # Middle -> End
    if nextBase == self.__middle.baseAsset:
      self.__actions.append('SELL')
      self.__actionWrappers.append('bids')
      nextBase = self.__middle.quoteAsset
    else:
      self.__actions.append('BUY')
      self.__actionWrappers.append('asks')
      nextBase = self.__middle.baseAsset

    self.__intermediates.append(nextBase)

    # End -> Base
    if nextBase == self.__end.baseAsset:
      self.__actions.append('SELL')
      self.__actionWrappers.append('bids')
    else:
      self.__actions.append('BUY')
      self.__actionWrappers.append('asks')
  
  def describe(self):
    return "{} from {}, then {} from {} and finally {} from {}".format(
      self.__actions[0], self.__start.text,
      self.__actions[1], self.__middle.text,
      self.__actions[2], self.__end.text
    )
  
  @property
  def text (self):
    return "{} -> {} -> {}".format(self.__base, self.__intermediates[0], self.__intermediates[1])

  @property
  def pairs (self):
    return [pair.symbol for pair in self]

  @property
  def actions (self):
    return self.__actions
  
  def __iter__ (self):
    yield from [self.__start, self.__middle, self.__end]

  def __str__ (self):
    return self.text
  
  def __repr__ (self):
    return self.text

  @property
  def workflow (self):
    yield from [
      (self.__start.symbol,  self.__actionWrappers[0]),
      (self.__middle.symbol, self.__actionWrappers[1]),
      (self.__end.symbol,    self.__actionWrappers[2]),
    ]