#!/bin/bash

docker build --compress --no-cache -t gabrielmilan/btrader:$(date '+%Y-%m-%d') .
docker build --compress -t gabrielmilan/btrader:latest .