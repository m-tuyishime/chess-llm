FROM python:3.11.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY . .

# Install wget, git, gcc, and development libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    git \
    build-essential \
    g++

# set up pip
RUN pip install --upgrade pip 

# install dependencies
RUN pip install -r requirements.txt

# install stockfish
RUN mkdir /stockfish
RUN wget https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-sse41-popcnt.tar \
    && tar -xvf stockfish-ubuntu-x86-64-sse41-popcnt.tar --strip-components=1 -C /stockfish \
    && rm stockfish-ubuntu-x86-64-sse41-popcnt.tar

# set up stockfish
RUN chmod +x /stockfish/stockfish-ubuntu-x86-64-sse41-popcnt
ENV STOCKFISH_PATH=/stockfish/stockfish-ubuntu-x86-64-sse41-popcnt