import devices
import os
import threading
import settings
import macros
import traceback
import time
from devices import cprint

try:
    devices.Modlist['logger'] = True

except ImportError as e:
    pass


#- Any early startup code for these devices
#def startup:

#- Any late shutdown code for these devices
def shutdown(setStatus,getStatus):
    device.fileh.close()

#- The Type attribute is used to declare what sort of device we need to return
#- otherwise is only used by the device module (this one)

def readSettings(settingsFile,devname):
    Dev = devices.Dev[devname]
    if Dev['Type'] == "log":
        Dev = devices.Dev[devname]
        Dev['BaseType'] = "log"
        device = type('', (), {})()

        if settingsFile.has_option(devname,"Output"):
            device.filename = settingsFile.get(devname,"Output")
            device.fileh = open(device.filename,"at")
        else:
            device.fileh = open("/dev/stderr","at")
        if 'Delay' in Dev:
            device.delay = Dev['Delay']
        else:
            device.delay = 0.0

        #- set the callbacks
        Dev['sendCommand'] = sendCommand
        Dev['getStatus'] = None
        Dev['setStatus'] = None
        Dev['getSensor'] = None
        return device
    else:
        return False

def sendCommand(command,device,deviceName,params):
    try:
        device.fileh.write(macros.expandVariables(command,params))
        device.fileh.write("\n")
        device.fileh.flush()
        os.fsync(device.fileh)
    except Exception as e:
        traceback.print_exc()
        cprint ("Error Writing to %s: %s" % (device.filename, e),"yellow")
        return False
    return True


devices.addReadSettings(readSettings)




