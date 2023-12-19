import sys
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import cv2
import pyds
import datetime
import numpy as np

PERSON_CLASS = 0
BAG_CLASS = 1
FACE_CLASS = 2
MUXER_BATCH_TIMEOUT_USEC = 33000
log_levels = {
    0: 'error',
    1: 'warning',
    2: 'info',
    3: 'debug',
    4: 'verbose',
    5: 'trace'
}
labels = ["Person", "Bag", "Face"]

def log_handler (
    category, 
    level, 
    file, 
    function, 
    line, 
    obj,
    message, 
    user_data
) :
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lvl = log_levels.get(level, 'debug')
    stdout_log(lvl, function, message.get())

def stdout_log (lvl, function, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{lvl}] [{function}] {message}"
    print(formatted_message)

class Pipeline:
    def __init__ (self, fps=30, model_config="config_infer_primary.txt"):
        self.pipe = None
        self.appsource = None
        self.video_convert_input = None
        self.caps_filter_input = None
        self.streammux = None
        self.infer = None
        self.video_convert_infer_output = None
        self.caps_filter_output = None
        self.video_convert_rgba_filter_output = None
        self.osd = None
        self.appsink = None
        self.model_config_path = model_config
        self.loop = None
        self.bus = None
        self.cap_fps = fps

    def osd_sink_pad_buffer_probe (pad,info,u_data):
        frame_number=0
        num_rects=0
        itr = 0

        gst_buffer = info.get_buffer()
        if not gst_buffer:
            print("Unable to get GstBuffer ")
            return

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list
        is_first_obj = True
        while l_frame is not None:
            try:
                # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
                # The casting is done by pyds.NvDsFrameMeta.cast()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone.
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            except StopIteration:
                break
            logg("debug", "osd", f"got frame_meta, height: {frame_meta.source_frame_height}, width: {frame_meta.source_frame_width}")
            obj_counter = {
                PERSON_CLASS:0,
                BAG_CLASS:0,
                FACE_CLASS:0
            }
            frame_number = frame_meta.frame_num
            l_obj=frame_meta.obj_meta_list
            n_frame = None
            is_first_frame = True
            while l_obj is not None:
                try:
                    # Casting l_obj.data to pyds.NvDsObjectMeta
                    obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break
                obj_counter[obj_meta.class_id] += 1
                # Periodically check for objects with borderline confidence value that may be false positive detections.
                # If such detections are found, annotate the frame with bboxes and confidence value.
                # Save the annotated frame to file.
                # Getting Image data using nvbufsurface
                # the input should be address of buffer and batch_id
                #logg("debug", "osd", "drawing bbox...")
                if is_first_frame : 
                    is_first_frame = False
                    n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                
                #n_frame = draw_bounding_boxes(n_frame, obj_meta, obj_meta.confidence)
                #logg("debug", "osd", "BBOX drawn")

                try:
                    l_obj = l_obj.next
                except StopIteration:
                    break
            print("Frame Number=", frame_number, "Number of Objects=", num_rects, "Person=",
                obj_counter[PERSON_CLASS], "Bag=", obj_counter[BAG_CLASS], "Face=", obj_counter[FACE_CLASS])
            # update frame rate through this probe
            stream_index = "stream{0}".format(frame_meta.pad_index)

            #frame_copy = np.array(n_frame, copy=True, order='C')
            #frame_copy = cv2.cvtColor(frame_copy, cv2.COLOR_RGBA2BGRA)
            #img_path = "{}.jpg".format(frame_number)
            #cv2.imwrite(img_path, frame_copy)
            try:
                l_frame = l_frame.next
            except StopIteration:
                break
                
        return Gst.PadProbeReturn.OK	

    def output_callback (sink):
        sample = sink.emit('pull-sample')
        buffer = sample.get_buffer()
        
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buffer))
        l_frame = batch_meta.frame_meta_list
        #import ipdb;ipdb.set_trace()

        return Gst.FlowReturn.OK

    def bus_call(self, bus, message, loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            sys.stdout.write("End-of-stream\n")
            loop.quit()
        elif t==Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            sys.stderr.write("Warning: %s: %s\n" % (err, debug))
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            sys.stderr.write("Error: %s: %s\n" % (err, debug))
            loop.quit()
        return True

    def init_elements (self):
        # Init elements
        width, height  = 960, 544
        self.pipe = Gst.Pipeline()
        self.appsource = Gst.ElementFactory.make("appsrc", "opencv-source")
        self.video_convert_input = Gst.ElementFactory.make("nvvideoconvert","video_convert_input")
        self.caps_filter_input = Gst.ElementFactory.make("capsfilter", "caps_filter_input")
        self.streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
        self.infer = Gst.ElementFactory.make("nvinfer", "infer")
        self.video_convert_infer_output = Gst.ElementFactory.make("nvvideoconvert", "video_convert_infer_output")
        self.caps_filter_output = Gst.ElementFactory.make("capsfilter", "caps_filter_output")
        self.video_convert_rgba_filter_output = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
        self.osd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        self.appsink = Gst.ElementFactory.make("appsink", "appsink")
        
        # Set  options
        caps1 = Gst.Caps.from_string("video/x-raw,format=RGBA,width=%d,height=%d,framerate=%d/1"%(width, height, self.cap_fps))
        caps2 = Gst.Caps.from_string("video/x-raw(memory:NVMM),format=NV12,width=%d,height=%d,framerate=%d/1"%(width, height, self.cap_fps))
        caps3 = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA,width=%d,height=%d"%(width, height))
        self.caps_filter_input.set_property('caps', caps2)
        self.caps_filter_output.set_property("caps", caps3)
        self.appsource.set_property('caps', caps1)
        mem_type = int(pyds.NVBUF_MEM_CUDA_UNIFIED)
        self.video_convert_infer_output.set_property("nvbuf-memory-type", mem_type)
        self.video_convert_rgba_filter_output.set_property("nvbuf-memory-type", mem_type)
        self.streammux.set_property("nvbuf-memory-type", mem_type)
        self.streammux.set_property('width', width)
        self.streammux.set_property('height', height)    
        self.streammux.set_property('batch-size', 1)
        self.infer.set_property('config-file-path', self.model_config_path)
        self.appsink.set_property('emit-signals', 'true')

    def link_elements (self):
        # Add to pipe
        self.pipe.add(self.appsource)
        self.pipe.add(self.video_convert_input)
        self.pipe.add(self.caps_filter_input)
        self.pipe.add(self.streammux)
        self.pipe.add(self.infer)
        self.pipe.add(self.video_convert_infer_output)
        self.pipe.add(self.caps_filter_output)
        self.pipe.add(self.video_convert_rgba_filter_output)
        self.pipe.add(self.osd)
        self.pipe.add(self.appsink)

        # Link one-by-one
        self.appsource.link(self.video_convert_input)
        self.video_convert_input.link(self.caps_filter_input)
        sinkpad = self.streammux.get_request_pad("sink_0")
        srcpad = self.caps_filter_input.get_static_pad("src")
        srcpad.link(sinkpad)
        self.streammux.link(self.infer)
        self.infer.link(self.video_convert_infer_output)
        self.video_convert_infer_output.link(self.caps_filter_output)
        self.caps_filter_output.link(self.video_convert_rgba_filter_output)
        self.video_convert_rgba_filter_output.link(self.osd)
        self.osd.link(self.appsink)

    def initialise (self, input_callback, output_callback):
        if not input_callback: 
            raise Exception("no input_callback given")
        if not output_callback:
            raise Exception("no output_callback given")

        # Init
        stdout_log("info", "main", "initialising...")
        Gst.init(None)
        Gst.debug_remove_log_function(None)
        Gst.debug_add_log_function(log_handler, None)
        self.init_elements()
        
        # Link
        stdout_log("info", "main", "linking elements ...")
        self.link_elements()

        # Add signals
        stdout_log(None, "main", "starting pipeline...")
        self.loop = GLib.MainLoop()
        self.bus = self.pipe.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect ("message", self.bus_call, self.loop)
        self.appsource.connect("need-data", input_callback, "need-data")
        self.appsink.connect('new-sample', output_callback)

    def run (self):
        self.pipe.set_state(Gst.State.PLAYING)
        try:
            self.loop.run()
        except:
            pass
        self.pipe.set_state(Gst.State.NULL)
        


