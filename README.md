# bTrader

[![Build Status](https://travis-ci.org/gabriel-milan/btrader.png?branch=master)](https://travis-ci.org/gabriel-milan/btrader)
[![Crate](https://img.shields.io/crates/v/btrader)](https://crates.io/crates/btrader)
[![Docker Image](https://img.shields.io/docker/v/gabrielmilan/btrader?logo=docker&sort=date)](https://hub.docker.com/r/gabrielmilan/btrader)

This is an arbitrage trading bot initially inspired by this [JS implementation](https://github.com/bmino/binance-triangle-arbitrage). For that reason, you'll find yourself comfortable with the configuration file for this if you have already tried the JS one.

For further information on the status of this bot, refer to [Development status](#development-status)

## Please support the project

If you've enjoyed bTrader, please consider supporting its development:

<a href="https://www.buymeacoffee.com/gabrielmilan" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

## Steps to run the bot

First of all, it's important to say that the great bottleneck for triangle arbitrage is related to network delays, not software performance. If you'd like better results, my recommendation is to rent a server with the lowest latency to `api.binance.com` as possible. In some places you'll find that the Binance servers may be located at Seattle(US), Tokyo(Japan) or even Isenburg(Germany). I haven't tried all locations, but I'm getting around 10ms latency on Saitama(Japan), which is probably fine.

Once you've decided what to do, generate your own configuration file, based on `config/sample_config.json`. It's pretty straightforward, but if you have any doubts please refer to the JS implementation [guide](https://github.com/bmino/binance-triangle-arbitrage/blob/master/config/readme.md). For Telegram stuff, refer to the [Telegram configuration](#telegram-configuration) section.

### The Docker method (easy way)

This method is the easy way to run this, but be aware that, by using Docker, performance may be a little worse. Use this for debugging purposes.

1. Please be sure that you have Docker installed and access to an user account with enough privilege to run containers.

2. Run the following command (note that `$(pwd)/config.json` is the path to your configuration file!)

```
docker run --net host -it --name btrader -v $(pwd)/config.json:/config.json gabrielmilan/btrader
```

**Note**: the `--net host` argument reduces networking overhead for the container.

### Compile and install (recommended)

This method envolves more steps, but it's recommended for performance.

1. Please be sure that you have Rust installed fully. If you don't, refer to [Install Rust](https://www.rust-lang.org/tools/install).

2. Clone this repository:

```
git clone https://github.com/gabriel-milan/btrader
```

3. `cd` into the repository directory and run:

```
cargo install --path .
```

4. You can then execute it by doing:

```
btrader /path/to/your/configuration/file.json
```

## Telegram configuration

- Generate a bot token with BotFather (official tutorial [here](https://core.telegram.org/bots#6-botfather))
- Get your Telegram user ID with the @userinfobot
- Fill the configuration file with your data (if you fill your user ID incorrectly, it will send messages to someone else!)
- Bot will notify you about executed trades or discovered deals, according to your config file

## Development status

- [x] Refactor from Python + Boost to Rust
- [x] Publish on [crates.io](https://crates.io/) (waiting on https://github.com/wisespace-io/binance-rs/pull/60)
- [ ] Configuration file checking
- [ ] Speed things up by computing trades in parallel
- [ ] Generate binary distributions
