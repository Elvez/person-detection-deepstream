#!/bin/bash

if [ "${DEVELOPER_MODE}" == "on" ]; then
    echo "Developer mode turned on. No autostart."
    sleep infinity
fi

./task_consumer.py



