import numpy as np
from google.protobuf.json_format import MessageToDict
import sys
import os
import json
from detectioninput_pb2 import DetectionInput
from detectionoutput_pb2 import DetectionOutput, Detection, Rect
from frame_pb2 import Frame, BatchFrame

def parse_frame (frame):
    """
    Input: Frame
    Output: tuple(nparray, shape, dtype)
    """
    if len(frame.matrix) == 0:
        return None, None, None
    shape = tuple(frame.shape)
    dtype = frame.dtype
    buff = frame.matrix
    return buff, shape, dtype

def parse_rect (rect):
    """
    Input: protobuf
    Output: dict
    """
    bbox = {}
    bbox["top"] = rect.top
    bbox["left"] = rect.left
    bbox["width"] = rect.width
    bbox["height"] = rect.height

    return bbox

def parse_detection_input (detection_input):
    """
    Input: protobuf
    Output: dict
    """
    task = {}
    task["feed_id"] = detection_input.feed_id
    task["feed_event_id"] = detection_input.feed_event_id
    buffer, shape, dtype = parse_frame(detection_input.frame)
    task['frame'] = buffer
    task['shape'] = shape
    task['dtype'] = dtype

    return task

def parse_detection_output (detection_output):
    """
    Input: protobuf
    Output: dict
    """
    task = {}
    input_task = parse_detection_input(detection_output.task)
    task["input_task"] = input_task
    task["detections"] = []
    for result in detection_output.results:
        detection = {}
        detection["label"] = result.label
        detection["score"] = result.score
        detection["crop"] = parse_rect(result.bbox)
        task["detections"].append(detection)

    return task
    
def parse_serialised_detection_output (payload):
    """
    Input: serialised protobuf
    Output: dict
    """
    detection_output = DetectionOutput()
    detection_output.ParseFromString(payload)
    task = parse_detection_output(detection_output)

    return task

def parse_serialised_detection_input (payload):
    """
    Input: serialised protobuf
    Output: dict
    """
    detection_input = DetectionInput()
    detection_input.ParseFromString(payload)
    task = parse_detection_input(detection_input)

    return task
