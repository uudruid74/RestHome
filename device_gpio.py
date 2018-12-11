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
                    sensor.sensorType = st = settingsFile.get(section,"type")
                    sensor.gpio = settingsFile.get(section,"gpio")
                    sensor.poll = poll = settingsFile.get(section,"poll") * 60
                    sensor.trigger = trigger = settingsFile.get(section, "trigger")
                    sensor.lastread = None #- Change this to read the status variable

                #- Note: When this event is popped, the POLL is detected.  We
                #- do a getSensor on it and then only perform the command if 
                #- the new value is different from what is saved in the GPIO
                #- definition.
                #-
                #- It's the poll process that checks the sensor.lastread and
                #- when it changes, writes the Status variable and runs trigger

                #macros.eventList.add("POLL_"+devname+"_"+sensorname,poll,trigger)
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
        return device
    except Exception as e:
        cprint ("GPIO device support requires Adafruit python module.\npip3 install Adafruit_BBIO", "red")
        traceback.print_exc()
        return None

#- We'll use this later to turn on/off GPIO buttons and switches
#def sendCommand(command,device,deviceName,params):
def getSensor(device,deviceName,sensorName,params):
    Dev = devices.Dev[deviceName]
    try:
        sensor = device.sensor[sensorName]
        oldvalue = sensor.lastread
        sensor.lastread = False
        if sensor.sensorType.startswith("temp"):
            reading = ADC.read(sensor.gpio)
            millivolts = reading * 1800  # 1.8V reference = 1800 mV
            temp_c = (millivolts - 500) / 10
            if sensor.sensorType == "tempC":
                sensor.lastread = tempC
            elif sensor.sensorType == "tempF":
                tempF = (temp_c * 9/5) + 32
                sensor.lastread = tempF
        if oldvalue is False or oldvalue is None:
            oldvalue = sensor.lastread
        return round((sensor.lastread+oldvalue)/2)
    except Exception as e:
        cprint ("Error finding sensor %s in %s: %s" % (sensorName,deviceName,e),"yellow")
        traceback.print_exc()
    return False


devices.addDiscover(discover)
devices.addReadSettings(readSettings)


