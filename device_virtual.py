import devices
from termcolor import cprint
from Crypto.Cipher import AES
from os import path
import threading
import settings
import macros
import traceback

try:
#- Any early startup code for these devices
#    def startup:

#- Any late shutdown code for these devices
#    def shutdown:

#- The Type attribute is used to declare what sort of device we need to return
#- otherwise is only used by the device module (this one)

    def readSettings(settingsFile,devname):
        Dev = devices.Dev[devname]
        if Dev['Type'] == 'Virtual':
            device = type('', (), {})()
            device.real = Dev['Actual']
            if device.real not in devices.Dev:
                cprint ("I can't find the %s device" % device.real, "yellow")
                return False
            Real = devices.Dev[device.real].copy()
            del Real['StartUpCommand']
            del Real['Comment']
            Dev.update(Real)
        else:
            return False
        if 'Delay' in Dev:
            device.delay = Dev['Delay']
        elif 'Delay' in devices.Dev[device.real]:
            device.delay = devices.Dev[device.real]['Delay']
        else:
            device.delay = 0.0
        Dev['learnCommand'] = learnCommand
        Dev['sendCommand'] = sendCommand
        Dev['getStatus'] = getStatus
        Dev['setStatus'] = setStatus
        Dev['getSensor'] = getSensor
        Dev['BaseType'] = 'virtual'
        return device


    def learnCommand(devname,device,params):
        if device.real in devices.DeviceByName:
            realdevice = devices.DeviceByName[device.real]
            Dev = devices.Dev[device.real]
            if 'deviceDelay' not in params:
                params['deviceDelay'] = realdevice.delay
            if 'learnCommand' in Dev and Dev['learnCommand'] is not None:
                return Dev['learnCommand'](devname,realdevice,params)
        return False


    def sendCommand(command,device,devname,params):
        if device.real in devices.DeviceByName:
            realdevice = devices.DeviceByName[device.real]
            Dev = devices.Dev[device.real]
            if 'deviceDelay' not in params:
                params['deviceDelay'] = realdevice.delay
            if 'sendCommand' in Dev and Dev['sendCommand'] is not None:
                return Dev['sendCommand'](command,realdevice,devname,params)
        return False


    def getStatus(device,deviceName,commandName,params):
        if device.real in devices.DeviceByName:
            realdevice = devices.DeviceByName[device.real]
            Dev = devices.Dev[device.real]
            if 'deviceDelay' not in params:
                params['deviceDelay'] = realdevice.delay
            if commandName == 'API_KEY':
                return 'REDIRECT %s' % device.real
            if 'getStatus' in Dev and Dev['getStatus'] is not None:
                return Dev['getStatus'](realdevice,deviceName,commandName,params)
        else:
            print ("No such device: %s real: %s" % (deviceName,device.real))
        return False


    def setStatus(deviceName,commandName,params,old,new):
        device = devices.DeviceByName[deviceName]
        if device.real in devices.DeviceByName:
            realdevice = devices.DeviceByName[device.real]
            Dev = devices.Dev[device.real]
            if 'deviceDelay' not in params:
                params['deviceDelay'] = realdevice.delay
            if 'setStatus' in Dev and Dev['setStatus'] is not None:
                return Dev['setStatus'](realdevice,deviceName,commandName,params,old,new)
        return False

    def getSensor(sensorName,params):
        if device.real in devices.DeviceByName:
            realdevice = devices.DeviceByName[device.real]
            Dev = devices.Dev[device.real]
            if 'deviceDelay' not in params:
                params['deviceDelay'] = realdevice.delay
            if 'getSensor' in Dev and Dev['getSensor'] is not None:
                return Dev['getSensor'](sensorName,params)
        return False

    devices.addReadSettings(readSettings)


except ImportError as e:
    cprint ("Virtual Device support is not available.  Please report this bug!", "red")


