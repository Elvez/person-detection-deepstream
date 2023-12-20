import numpy as np
from google.protobuf.json_format import MessageToDict
import sys
import os
import json
from proto.detectioninput_pb2 import DetectionInput
from proto.detectionoutput_pb2 import DetectionOutput, Detection, Rect
from proto.frame_pb2 import Frame, BatchFrame

