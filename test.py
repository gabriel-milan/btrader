import logging
from btrader import bTrader

LOG_TO_FILE = False

if LOG_TO_FILE:
  log_file='a.log'
else:
  log_file=None

a = bTrader('config.json', log_file=log_file)
a.setDaemon(False)
a.start()