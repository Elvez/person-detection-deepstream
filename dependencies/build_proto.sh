#!/bin/bash

echo "[jarvis] building protocol-buffers ..."
cd /root/jarvis-consumer/proto &&
protoc --python_out=../app * &&
echo "[jarvis] building done!"

