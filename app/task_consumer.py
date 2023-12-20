#!/usr/bin/python

import os
from config import *
from pipeline import *

SAMPLE_FRAME_PATH = "/root/sample.jpeg"
fframe = cv2.imread(SAMPLE_FRAME_PATH)
fframe = cv2.resize(fframe, (960, 544))
fframe = cv2.cvtColor(fframe, cv2.COLOR_BGR2RGBA)

def init_redis ():
    pass

def input_callback (appsource, _size, u_data):
    # get frame from redis
    Pipeline.push_frame(fframe)

def output_callback (sink):
    results = Pipeline.get_results_dict(sink)
    if not results:
        return Gst.FlowReturn.OK
    else:
        stdout_log("info", "output", f"results: {str(results)}")

if __name__ == "__main__":
    stdout_log("info", "task_consumer", "starting ...")
    pipe = Pipeline(PROCESSING_FPS, "/root/jarvis-consumer/peopleNet/config_infer_primary_peoplenet.txt")
    pipe.initialise(input_callback, output_callback)
    pipe.run()