import json
import logging
from time import time
from btrader.extensions import Deal
from btrader.bot import TelegramBot

with open ("test/config.json", "r") as f:
  cfg = json.loads(f.read())
  f.close()

bot = TelegramBot(cfg["TELEGRAM"]["TOKEN"], user_id=cfg["TELEGRAM"]["USER_ID"])
bot.start()

deal = Deal()
bot.sendDeal(deal, 30)
bot.sendDeal(deal, 40)
bot.sendDeal(deal, 50)
bot.sendMessage ("Yay!")