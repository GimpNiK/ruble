FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Обновляем и устанавливаем зависимости (без PPA)
RUN apt-get update && apt-get install -y \
    git \
    zip \
    unzip \
    python3 \
    python3-pip \
    python3-dev \
    openjdk-17-jdk \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libtinfo5 \
    cmake \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Buildozer
RUN pip3 install --upgrade pip buildozer cython

WORKDIR /home/user/app

CMD ["bash"]