FROM debian:buster

LABEL maintainer "Gabriel Gazola Milan <gabriel.gazola@poli.ufrj.br>"

# Initial setup
ENV LC_ALL C.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV TERM screen
USER root
SHELL [ "/bin/bash", "-c" ]
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Dependencies
RUN apt update && apt upgrade -y && apt install -y git python3 python3-pip

# Get bot
RUN python3 -m pip install btrader
RUN cd / && git clone https://github.com/gabriel-milan/btrader

# Set command
CMD /btrader/scripts/entrypoint.py