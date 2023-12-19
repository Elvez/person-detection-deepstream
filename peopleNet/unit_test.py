import sys
sys.path.append('../')
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
SAMPLE_FRAME_PATH = "/root/sample.jpeg"
fframe = cv2.imread(SAMPLE_FRAME_PATH)
fframe = cv2.resize(fframe, (960, 544))
fframe = cv2.cvtColor(fframe, cv2.COLOR_BGR2RGBA)
log_levels = {
    0: 'error',
    1: 'warning',
    2: 'info',
    3: 'debug',
    4: 'verbose',
    5: 'trace'
}
pgie_classes_str = ["Person", "Bag", "Face"]

def bus_call(bus, message, loop):
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
    logg(lvl, function, message.get())

def logg(lvl, function, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{lvl}] [{function}] {message}"
    print(formatted_message)

def push_buffer(appsource, _size, u_data):
    appsource.emit("push-buffer", Gst.Buffer.new_wrapped(fframe.tobytes()))

def draw_bounding_boxes(image, obj_meta, confidence):
    confidence = '{0:.2f}'.format(confidence)
    rect_params = obj_meta.rect_params
    top = int(rect_params.top)
    left = int(rect_params.left)
    width = int(rect_params.width)
    height = int(rect_params.height)
    obj_name = pgie_classes_str[obj_meta.class_id]
    # image = cv2.rectangle(image, (left, top), (left + width, top + height), (0, 0, 255, 0), 2, cv2.LINE_4)
    color = (0, 0, 255, 0)
    w_percents = int(width * 0.05) if width > 100 else int(width * 0.1)
    h_percents = int(height * 0.05) if height > 100 else int(height * 0.1)
    linetop_c1 = (left + w_percents, top)
    linetop_c2 = (left + width - w_percents, top)
    image = cv2.line(image, linetop_c1, linetop_c2, color, 6)
    linebot_c1 = (left + w_percents, top + height)
    linebot_c2 = (left + width - w_percents, top + height)
    image = cv2.line(image, linebot_c1, linebot_c2, color, 6)
    lineleft_c1 = (left, top + h_percents)
    lineleft_c2 = (left, top + height - h_percents)
    image = cv2.line(image, lineleft_c1, lineleft_c2, color, 6)
    lineright_c1 = (left + width, top + h_percents)
    lineright_c2 = (left + width, top + height - h_percents)
    image = cv2.line(image, lineright_c1, lineright_c2, color, 6)
    # Note that on some systems cv2.putText erroneously draws horizontal lines across the image
    image = cv2.putText(image, obj_name + ',C=' + str(confidence), (left - 10, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 0, 255, 0), 2)
    return image

def osd_sink_pad_buffer_probe(pad,info,u_data):
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

def on_new_sample(sink):
    sample = sink.emit('pull-sample')
    buffer = sample.get_buffer()
    
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buffer))
    l_frame = batch_meta.frame_meta_list
    #import ipdb;ipdb.set_trace()

    return Gst.FlowReturn.OK

def main(args):
    width  = 960
    height = 544
    Gst.init(None)
    Gst.debug_remove_log_function(None)
    Gst.debug_add_log_function(log_handler, None)
    logg(None, "main", "creating Pipeline ...")
    pipeline = Gst.Pipeline()
    appsource = Gst.ElementFactory.make("appsrc", "opencv-source")
    nvvideoconvert = Gst.ElementFactory.make("nvvideoconvert","nv-videoconv")
    caps_filter = Gst.ElementFactory.make("capsfilter","capsfilter")
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    sink = Gst.ElementFactory.make("appsink", "sink")
    caps1 = Gst.Caps.from_string("video/x-raw,format=RGBA,width=%d,height=%d,framerate=30/1"%(width, height))
    caps2 = Gst.Caps.from_string("video/x-raw(memory:NVMM),format=NV12,width=%d,height=%d,framerate=30/1"%(width, height))
    caps3 = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA,width=%d,height=%d"%(width, height))
    rgbafilter = Gst.ElementFactory.make("capsfilter", "rgbafilter")
    rgbafilter.set_property("caps", caps3)
    mem_type = int(pyds.NVBUF_MEM_CUDA_UNIFIED)
    nvvidconv.set_property("nvbuf-memory-type", mem_type)
    streammux.set_property("nvbuf-memory-type", mem_type)
    nvvidconv1.set_property("nvbuf-memory-type", mem_type)

    appsource.set_property('caps', caps1)
    caps_filter.set_property('caps',caps2)
    streammux.set_property('width', width)
    streammux.set_property('height', height)    
    streammux.set_property('batch-size', 1)
    pgie.set_property('config-file-path', "config_infer_primary_peoplenet.txt")
    sink.set_property('emit-signals', 'true')
    pipeline.add(appsource)
    pipeline.add(nvvideoconvert)
    pipeline.add(caps_filter)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvvidconv)
    pipeline.add(rgbafilter)
    pipeline.add(nvvidconv1)
    pipeline.add(nvosd)
    pipeline.add(sink)

    logg(None, "main", "L=linking elements in the Pipeline...")
    appsource.link(nvvideoconvert)
    nvvideoconvert.link(caps_filter)
    sinkpad = streammux.get_request_pad("sink_0")
    srcpad = caps_filter.get_static_pad("src")
    srcpad.link(sinkpad)
    streammux.link(pgie)
    pgie.link(nvvidconv)
    nvvidconv.link(rgbafilter)
    rgbafilter.link(nvvidconv1)
    nvvidconv1.link(nvosd)
    nvosd.link(sink)
    sink.connect('new-sample', on_new_sample)

    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)
    appsource.connect("need-data", push_buffer, "need-data")
    osdsinkpad = nvosd.get_static_pad("sink")
    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

    logg(None, "main", "starting pipeline...")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    # cleanup
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

