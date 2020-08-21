import logging
from btrader import bTrader

LOG_TO_FILE = False

if LOG_TO_FILE:
  log_file='a.log'
else:
  log_file=None

a = bTrader('test/config.json', log_file=log_file)
a.run()