import logging
from btrader import bTrader

a = bTrader('config.json')
a.getWebsockets()