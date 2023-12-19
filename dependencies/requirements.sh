#!/bin/bash

echo "[jarvis] installing dependencies ...";
apt update &&\
apt install -y \
    python3-gi \
    python3-dev \
    python3-gst-1.0 \
    python3-pip \
    nano \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer1.0-dev \
    libx11-dev \
    libcairo2-dev &&\
echo "[jarvis] done!"
