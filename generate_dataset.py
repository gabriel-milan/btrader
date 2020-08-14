import struct
import numpy as np
from redis import Redis
from btrader.core import bTrader

def npFromRedis (r, key, dims):
  encoded = r.get(key)
  arr = None
  if encoded is None:
    return arr
  if dims == 1:
    a = struct.unpack('>I', encoded[:4])
    arr = np.frombuffer(encoded[4:]).reshape(a)
  elif dims == 2:
    a, b = struct.unpack('>II', encoded[:8])
    arr = np.frombuffer(encoded[8:]).reshape(a, b)
  elif dims == 3:
    a, b, c = struct.unpack('>III', encoded[:12])
    arr = np.frombuffer(encoded[12:]).reshape(a, b, c)
  return arr

r = Redis()
trader = bTrader("bTrader.json")

for symbol in trader.symbols:
  X = npFromRedis(r, "X_{}".format(symbol), 3)
  y = npFromRedis(r, "y_{}".format(symbol), 1)
  np.savez("data_{}".format(symbol), X=X, y=y)