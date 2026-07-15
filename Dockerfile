FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev \
    zlib1g-dev libgstreamer1.0-dev gstreamer1.0-plugins-base \
    libmtdev-dev libgl1-mesa-dev libgles2-mesa-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV KIVY_NO_CONSOLELOG=1

CMD ["python", "main.py"]
