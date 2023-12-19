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
    appsource.emit("push-buffer", Gst.Buffer.new_wrapped(fframe.tobytes()))

def output_callback (sink):
    sample = sink.emit('pull-sample')
    buffer = sample.get_buffer()
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buffer))
    l_frame = batch_meta.frame_meta_list
    results = []
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break
        frame_number = frame_meta.frame_num
        l_obj = frame_meta.obj_meta_list
        num_rects = frame_meta.num_obj_meta
        stdout_log("info", "output", f"got {num_rects} detections")
        result = []
        while l_obj is not None:
            detection = {}
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                detection["label"] = labels[obj_meta.class_id]
                detection["score"] = '{0:.2f}'.format(obj_meta.confidence)
                top = int(obj_meta.rect_params.top)
                left = int(obj_meta.rect_params.left)
                width = int(obj_meta.rect_params.width)
                height = int(obj_meta.rect_params.height)
                detection["bbox"] = [top, left, width, height]
                result.append(detection)
            except StopIteration:
                break
                
            try:
                l_obj = l_obj.next
            except StopIteration:
                break
        results.append(result)
        stdout_log("info", "output", f"results: {str(results)}")
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.FlowReturn.OK

if __name__ == "__main__":
    stdout_log("info", "task_consumer", "starting ...")
    pipe = Pipeline(PROCESSING_FPS, "/root/jarvis-consumer/peopleNet/config_infer_primary_peoplenet.txt")
    pipe.initialise(input_callback, output_callback)
    pipe.run()