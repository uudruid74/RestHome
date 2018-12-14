import devices
from termcolor import cprint
from os import path
import threading
import settings
import macros
import traceback
import time

try:
    import Adafruit_BBIO.ADC as ADC

    devices.Modlist['gpio'] = True

except ImportError as e:
    pass


#- Any early startup code for these devices
#    def startup:

#- Any late shutdown code for these devices
#    def shutdown:

#- Attempt to discover devices and create appropriate settings file
#- entries for those devices

def discover(settingsFile,timeout,listen,broadcast):
    if 'gpio' not in devices.Modlist:
        cprint ("GPIO device support requires Adafruit python module.\npip3 install Adafruit_BBIO", "red")
        return False
    print ("\tDetecting GPIO devices is currently unsupported...")

#- The Type attribute is used to declare what sort of device we need to return
#- otherwise is only used by the device module (this one)

def readSettings(settingsFile,devname):
    try:
        Dev = devices.Dev[devname]
        device = type('', (), {})()
        if Dev['Type'] == 'GPIO':
            device.sensor = {}
            for section in settingsFile.sections():
                if section.startswith("GPIO "):
                    sensorname = section[5:]
                    sensor = device.sensor[sensorname] = type('', (), {})()
                    sensor.sensorType = settingsFile.get(section,"type")
                    sensor.gpio = settingsFile.get(section,"gpio")
                    sensor.lastread = False
                    if settingsFile.has_option(section,"poll"):
                        sensor.poll = float(settingsFile.get(section,"poll")) * 60
                    else:
                        sensor.poll = 300.0       #- 5 minutes
                    if settingsFile.has_option(section,"trigger"):
                        sensor.trigger = trigger = settingsFile.get(section, "trigger")
                        initialparams = {}
                        initialparams['device'] = devname
                        macros.eventList.add("POLL_"+devname+"_"+sensorname,2.0,sensor.trigger,initialparams)
                    sensor.lastread = None #- Change this to read the status variable
        else:
            return False
        ADC.setup();
        if 'Delay' in Dev:
            device.delay = Dev['Delay']
        else:
            device.delay = 0.0

        #- set the callbacks
        Dev['learnCommand'] = None
        Dev['sendCommand'] = None
        Dev['getStatus'] = None
        Dev['setStatus'] = None
        Dev['getSensor'] = getSensor
        Dev['BaseType'] = "gpio"
        Dev['pollCallback'] = pollCallback

        return device
    except Exception as e:
        cprint ("GPIO device support requires Adafruit python module.\npip3 install Adafruit_BBIO", "red")
        traceback.print_exc()
        return None

#- We'll use this later to turn on/off GPIO buttons and switches
#def sendCommand(command,device,deviceName,params):

def getSensor(sensorName,params):
    devicename = params['device']
    device = devices.DeviceByName[devicename]
    Dev = devices.Dev[devicename]
    try:
        sensor = device.sensor[sensorName]
        if sensor.sensorType.startswith("temp"):
            reading1 = ADC.read(sensor.gpio)
            time.sleep(0.5)
            reading2 = ADC.read(sensor.gpio)
            reading = (reading1+reading2)/2
            millivolts = reading * 1800  # 1.8V reference = 1800 mV
            temp_c = (millivolts - 500) / 10
            if sensor.sensorType == "tempC":
                sensor.lastread = tempC
            elif sensor.sensorType == "tempF":
                tempF = (temp_c * 9/5) + 32
                sensor.lastread = tempF
        value = round(sensor.lastread)
        params['value'] = value
        return value
    except Exception as e:
        cprint ("Error finding sensor %s in %s: %s" % (sensorName,devicename,e),"yellow")
        traceback.print_exc()
    return False


# Polling is an event named "POLL_devicename_argname"
def pollCallback(devicename,argname,command,params):
    device = devices.DeviceByName[devicename]
    sensor = device.sensor[argname]
    oldvalue = sensor.lastread
    newvalue = getSensor(argname,params)
    macros.eventList.add("POLL_"+devicename+"_"+argname,sensor.poll,sensor.trigger,params)

    if oldvalue != newvalue:
        return newvalue
    else:
        return False


devices.addDiscover(discover)
devices.addReadSettings(readSettings)


