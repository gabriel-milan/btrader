__all__ = [
  'Logger'
]

import logging
import concurrent.futures

class LogFormatter (logging.Formatter):
  
  # Regular colors
  black         = '\033[0;30m'
  red           = '\033[0;31m'
  green         = '\033[0;32m'
  yellow        = '\033[0;33m'
  blue          = '\033[0;34m'
  magenta       = '\033[0;35m'
  cyan          = '\033[0;36m'
  white         = '\033[0;37m'
  # Bold colors
  bold_black    = '\033[1;30m'
  bold_red      = '\033[1;31m'
  bold_green    = '\033[1;32m'
  bold_yellow   = '\033[1;33m'
  bold_blue     = '\033[1;34m'
  bold_magenta  = '\033[1;35m'
  bold_cyan     = '\033[1;36m'
  bold_white    = '\033[1;37m'
  # Reset
  reset_seq     = "\033[0m"

  format = "%(asctime)s | %(name)-9.9s %(levelname)8.8s -> %(message)s"

  FORMATS = {
    logging.DEBUG: bold_white + format + reset_seq,
    logging.INFO: green + format + reset_seq,
    logging.WARNING: bold_yellow + format + reset_seq,
    logging.ERROR: red + format + reset_seq,
    logging.CRITICAL: bold_red + format + reset_seq
  }

  def format(self, record):
    log_fmt = self.FORMATS.get(record.levelno)
    formatter = logging.Formatter(log_fmt)
    return formatter.format(record)

class Logger (logging.Logger):

  def __init__ (self, name="Logger", level=logging.DEBUG, filename=None):
    super().__init__(name=name, level=level)
    self.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(LogFormatter())
    self.addHandler(ch)
    if filename:
      if ".log" not in filename:
        filename += '.log'
      fl = logging.FileHandler(filename)
      fl.setLevel(level)
      fl.setFormatter(LogFormatter())
      self.addHandler(fl)
    self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

  def debug (self, msg, *args, **kwargs):
    self.__executor.submit(super().debug, msg, *args, **kwargs)

  def info (self, msg, *args, **kwargs):
    self.__executor.submit(super().info, msg, *args, **kwargs)

  def warning (self, msg, *args, **kwargs):
    self.__executor.submit(super().warning, msg, *args, **kwargs)

  def error (self, msg, *args, **kwargs):
    self.__executor.submit(super().error, msg, *args, **kwargs)

  def critical (self, msg, *args, **kwargs):
    self.__executor.submit(super().critical, msg, *args, **kwargs)

  def shutdown (self):
    self.__executor.shutdown()