__all__ = [
  'TelegramBot'
]

import logging
import telegram
from time import time
from functools import partial
from telegram.ext import Updater
from telegram.ext import CommandHandler

from btrader.extensions import Deal
from btrader.core.Logger import Logger
from btrader.core.StoppableThread import StoppableThread

class TelegramBot (StoppableThread):

  def __init__ (self, token, user_id=0, trader_matrix=None, level=logging.DEBUG, log_file=None, *args, **kwargs):
    super(TelegramBot, self).__init__(*args, **kwargs)
    self.__logger = Logger(name="TelegramBot", level=level, filename=log_file)
    self.__token = token
    self.__userId = user_id if user_id != 0 else None
    self.__bot = telegram.Bot(token=self.__token)
    self.__updater = Updater(token=self.__token, use_context=True)
    self.__dispatcher = self.__updater.dispatcher
    self.__jobQueue = self.__updater.job_queue
    self.__handlers = []
    self.__handlers.append(CommandHandler('start', self.__start))
    self.__handlers.append(CommandHandler('age', self.__age))
    self.__initialized = False
    self.__defaultHello = "Well, hello there! You're the default user configured for this bot."
    self.__traderMatrix = trader_matrix

  @property
  def logger (self):
    return self.__logger

  @property
  def updater (self):
    return self.__updater

  @property
  def dispatcher (self):
    return self.__dispatcher

  @property
  def jobQueue (self):
    return self.__jobQueue

  @property
  def isInitialized (self):
    return self.__initialized
  
  def __start (self, update, context):
    if (self.__userId is not None):
      if (self.__userId == update.effective_chat.id):
        self.logger.debug("/start required by correct user")
        context.bot.send_message(chat_id=update.effective_chat.id, text=self.__defaultHello)
      else:
        self.logger.debug("/start required by unknown user, not responding")
    else:
      self.__userId = update.effective_chat.id
      self.logger.debug("/start required by first user, setting userId to {}".format(self.__userId))
      context.bot.send_message(chat_id=update.effective_chat.id, text=self.__defaultHello)

  def __age (self, update, context):
    if (self.__userId is not None):
      if (self.__userId == update.effective_chat.id):
        self.logger.debug("/age required by correct user")
        if (self.__traderMatrix is not None):
          avg, std, best = self.__traderMatrix.getAverageAge()
          context.bot.send_message(chat_id=update.effective_chat.id, text="Age (ms): {:.2f}+-{:.2f} (latest best is {:.2f}ms)".format(avg, std, best))
        else:
          context.bot.send_message(chat_id=update.effective_chat.id, text="Average age not available")
      else:
        self.logger.debug("/age required by unknown user, not responding")
    else:
      self.logger.debug("/age required but no userId is configured")

  def __scheduleMessage (self, message: str, context: telegram.ext.CallbackContext):
    context.bot.send_message(chat_id=self.__userId, text=message)

  def sendMessage (self, msg: str):
    if (self.__userId is not None):
      self.jobQueue.run_once(partial(self.__scheduleMessage, msg), when=0, name="sendMessage")

  def sendDeal (self, deal: Deal, age: float):
    if (self.__userId is not None):
      msg = ">>>> New deal available\n"
      msg += "- Data age: {:.2f}ms\n".format(age)
      msg += "- Expected profit: {:.4f}%\n".format(deal.getProfit()*100)
      for i, action in enumerate(deal.getActions()):
        msg += "- Trade #{}: {} {} from pair {}\n".format(
          i+1,
          action.getAction(),
          round(action.getQuantity(), 8),
          action.getPair()
        )
      self.jobQueue.run_once(partial(self.__scheduleMessage, msg), when=0, name="sendDeal")

  def initialize (self):
    for handler in self.__handlers:
      self.dispatcher.add_handler(handler)
    self.__initialized = True

  def run (self):
    if not self.isInitialized:
      self.initialize()
    self.__updater.start_polling()