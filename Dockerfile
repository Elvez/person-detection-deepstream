FROM nvcr.io/nvidia/deepstream:6.3-samples
LABEL MAINTAINER="pravesh.soni@staqu.com"

WORKDIR /root/jarvis-consumer
COPY dependencies/ /root/jarvis-consumer/dependencies

RUN ["/bin/bash", "/root/jarvis-consumer/dependencies/requirements.sh"]
RUN ["/bin/bash", "-c", "pip install -r /root/jarvis-consumer/dependencies/requirements.txt"]
RUN ["/bin/bash", "-c", "pip install /root/jarvis-consumer/dependencies/pyds-1.1.8-py3-none-linux_x86_64.whl"]

COPY peopleNet/ /root/jarvis-consumer/peopleNet
COPY app/ /root/jarvis-consumer/app
COPY entrypoint.sh /root/jarvis-consumer/

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
