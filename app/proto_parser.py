import numpy as np
from google.protobuf.json_format import MessageToDict
import sys
import os
import json
from detectioninput_pb2 import DetectionInput
from detectionoutput_pb2 import DetectionOutput, Detection, Rect
from frame_pb2 import Frame, BatchFrame

