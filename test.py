import time
import ctypes
import requests
import threading
from ctypes.util import find_library
from pynput import keyboard

MultitouchSupport = ctypes.CDLL("/System/Library/PrivateFrameworks/MultitouchSupport.framework/MultitouchSupport")

CFArrayRef = ctypes.c_void_p
CFMutableArrayRef = ctypes.c_void_p
CFIndex = ctypes.c_long
CFArrayGetCount = MultitouchSupport.CFArrayGetCount
CFArrayGetCount.argtypes = [CFArrayRef]
CFArrayGetCount.restype = CFIndex
CFArrayGetValueAtIndex = MultitouchSupport.CFArrayGetValueAtIndex
CFArrayGetValueAtIndex.argtypes = [CFArrayRef, CFIndex]
CFArrayGetValueAtIndex.restype = ctypes.c_void_p
MTDeviceCreateList = MultitouchSupport.MTDeviceCreateList
MTDeviceCreateList.argtypes = []
MTDeviceCreateList.restype = CFMutableArrayRef

class MTPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float),
                ("y", ctypes.c_float)]

class MTVector(ctypes.Structure):
    _fields_ = [("position", MTPoint),
                ("velocity", MTPoint)]

class MTData(ctypes.Structure):
    _fields_ = [
      ("frame", ctypes.c_int),
      ("timestamp", ctypes.c_double),
      ("identifier", ctypes.c_int),
      ("state", ctypes.c_int),  # Current state (of unknown meaning).
      ("unknown1", ctypes.c_int),
      ("unknown2", ctypes.c_int),
      ("normalized", MTVector),  # Normalized position and vector of
                                 # the touch (0 to 1).
      ("size", ctypes.c_float),  # The area of the touch.
      ("unknown3", ctypes.c_int),
      
      # The following three define the ellipsoid of a finger.
      ("angle", ctypes.c_float),
      ("major_axis", ctypes.c_float),
      ("minor_axis", ctypes.c_float),
      ("unknown4", MTVector),
      ("unknown5_1", ctypes.c_int),
      ("unknown5_2", ctypes.c_int),
      ("unknown6", ctypes.c_float),
    ]

MTDataRef = ctypes.POINTER(MTData)

MTContactCallbackFunction = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, MTDataRef,
    ctypes.c_int, ctypes.c_double, ctypes.c_int)

MTDeviceRef = ctypes.c_void_p

MTRegisterContactFrameCallback = MultitouchSupport.MTRegisterContactFrameCallback
MTRegisterContactFrameCallback.argtypes = [MTDeviceRef, MTContactCallbackFunction]
MTRegisterContactFrameCallback.restype = None

MTDeviceStart = MultitouchSupport.MTDeviceStart
MTDeviceStart.argtypes = [MTDeviceRef, ctypes.c_int]
MTDeviceStart.restype = None

server_address = 'http://localhost:8080/get'

@MTContactCallbackFunction
def my_callback(device, data_ptr, n_fingers, timestamp, frame):
    
    # print threading.current_thread(), device, data_ptr, n_fingers, timestamp, frame
    
    for i in xrange(n_fingers):
        data = data_ptr[i]
        d = "x=%.2f, y=%.2f" % (data.normalized.position.x * 100,
                                data.normalized.position.y * 100)
        # print "%d: %s" % (i, d)

        if i == 0:
            # tilt in y (-30, 210)
            # pan in x (-175, 175)
            # ftp://ftp.panasonic.com/provideo/awhe130/aw-he130_ip_control_specification_aw-he40_aw-ue70.pdf
            # AW-HE130

            tilt = remap(data.normalized.position.y, 0, 1, 0, 65535)   
            pan = remap(data.normalized.position.x, 0, 1, 0, 65535)
            pan_hex = str(format(int(pan), '#06x'))[2:]
            tilt_hex = str(format(int(tilt), '#06x'))[2:]
            
            # print('pan', pan, 'tilt', tilt)
            # print('pan_hex', pan_hex, 'tilt_hex', tilt_hex)

            command = '#APC' + pan_hex + tilt_hex
            payload = {'cmd': command, 'res': 1}
            
            # payload = {'finger': i, 'x': data.normalized.position.x, 'y': data.normalized.position.y, 'n_fingers': n_fingers, 'timestamp': timestamp, 'frame': frame, 'res': 1}

            r = requests.get(server_address, params=payload)
    return 0

def on_press(key):
    try:
        print('alphanumeric key {0} pressed'.format(
            key.char))
    except AttributeError:
        print('special key {0} pressed'.format(
            key))

def on_release(key):
    print('{0} released'.format(
        key))
    
    if key == keyboard.Key.ctrl:
        command = '#PTS5050'
        payload = {'cmd': command, 'res': 1}
        r = requests.get(server_address, params=payload)

    if key == keyboard.Key.esc:
        # Stop listener
        return False

def remap( x, oMin, oMax, nMin, nMax ):

    #range check
    if oMin == oMax:
        print "Warning: Zero input range"
        return None

    if nMin == nMax:
        print "Warning: Zero output range"
        return None

    #check reversed input range
    reverseInput = False
    oldMin = min( oMin, oMax )
    oldMax = max( oMin, oMax )
    if not oldMin == oMin:
        reverseInput = True

    #check reversed output range
    reverseOutput = False   
    newMin = min( nMin, nMax )
    newMax = max( nMin, nMax )
    if not newMin == nMin :
        reverseOutput = True

    portion = (x-oldMin)*(newMax-newMin)/(oldMax-oldMin)
    if reverseInput:
        portion = (oldMax-x)*(newMax-newMin)/(oldMax-oldMin)

    result = portion + newMin
    if reverseOutput:
        result = newMax - portion

    return result

devices = MultitouchSupport.MTDeviceCreateList()
num_devices = CFArrayGetCount(devices)

print "num_devices =", num_devices

for i in xrange(num_devices):
    device = CFArrayGetValueAtIndex(devices, i)
    print "device #%d: %016x" % (i, device)
    
    MTRegisterContactFrameCallback(device, my_callback)
    MTDeviceStart(device, 0)

with keyboard.Listener( 
    on_press=on_press,
    on_release=on_release) as listener:
        listener.join() 
    
while threading.active_count():
    time.sleep(0.130)