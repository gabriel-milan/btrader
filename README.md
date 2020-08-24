# bTrader

This is an arbitrage trading bot based on this [JS implementation](https://github.com/bmino/binance-triangle-arbitrage). For that reason, the configuration files for both of them are fully compatible.

## Steps to run the bot

Two-step process:

1. Read the configuration guide from [here](https://github.com/bmino/binance-triangle-arbitrage/blob/master/config/readme.md). I was lazy to write one of my own, so you can read it from the JS implementation repository. After that, generate your own configuration file or just edit the one on the `config/` directory on this repository.

2. (Recommended) Use the Docker image (`$(pwd)/config.json` is the path to your configuration file):

```
docker run -it --name btrader -v $(pwd)/config.json:/config.json gabrielmilan/btrader
```

2. (Few more steps) Use the Python package:

```
python3 -m pip install btrader
python3
>>>> from btrader import bTrader
>>>> bot = bTrader("config.json")
>>>> bot.run()
```

## Development status

- [x] C++ implementation of calculations
- [x] Monitoring websockets
- [x] Computing profits over all possible triangles
- [x] Filtering and showing viable operations
- [x] Implement asset step size
- [x] Structure for holding trading actions and quantities
- [x] Perform trading actions
- [ ] Checking configuration file
- [ ] Best deals printing
- [ ] Telegram bot
- [ ] Generate binary distributions

## Config file compatibility

- [x] KEYS
- [x] INVESTMENT
- [x] TRADING [ENABLED, EXECUTION_CAP, TAKER_FEE, PROFIT_THRESHOLD, AGE_THRESHOLD]
- [ ] TRADING [EXECUTION_STRATEGY, EXECUTION_TEMPLATE]
- [ ] HUD
- [ ] LOG
- [x] DEPTH [SIZE]
- [ ] DEPTH [PRUNE, INITIALIZATION_INTERVAL]
- [ ] TIMING
