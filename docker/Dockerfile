FROM rust:1.48-buster

LABEL maintainer "Gabriel Gazola Milan <gabriel.gazola@poli.ufrj.br>"

# Initial setup
ENV LC_ALL C.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV TERM screen
USER root
SHELL [ "/bin/bash", "-c" ]
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Get code
WORKDIR /
RUN git clone https://github.com/gabriel-milan/btrader code

# Install
RUN cp /code/config/sample_config.json /config.json
WORKDIR /code
RUN cargo install --path .

# Set command
CMD btrader /config.json