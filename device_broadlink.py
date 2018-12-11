import devices
from termcolor import cprint
from Crypto.Cipher import AES
from os import path
import threading
import settings
import macros
import binascii
import traceback
import time

try:
    import broadlink

    devices.Modlist['broadlink'] = True

except ImportError as e:
    pass


#- Any early startup code for these devices
#    def startup:

#- Any late shutdown code for these devices
#    def shutdown:

#- Attempt to discover devices and create appropriate settings file
#- entries for those devices

def discover(settingsFile,timeout,listen,broadcast):
    if 'broadlink' not in devices.Modlist:
        cprint ("Broadlink device support requires broadlink python module.\npip3 install broadlink", "red")
        return False
    print ("\tDetecting Broadlink devices ...")
    try:
        broadlinkDevices = broadlink.discover(timeout,listen,broadcast)
    except:
        broadlinkDevices = broadlink.discover(timeout,listen)

    settings.backupSettings()
    try:
        ControlIniFile = open(path.join(settings.applicationDir, 'settings.ini'), 'w')
        for device in broadlinkDevices:
            try:
                device.hostname = socket.gethostbyaddr(device.host[0])[0]
                if "." in device.hostname:
                    device.hostname = device.hostname.split('.')[0]
            except:
                device.hostname = "Broadlink" + device.type.upper()
            if device.hostname in devices.DeviceByName:
                device.hostname = "%s-%s" % (device.hostname, str(device.host).split('.')[3])
            if not settingsFile.has_section(device.hostname):
                settingsFile.add_section(device.hostname)
            settingsFile.set(device.hostname,'IPAddress',str(device.host[0]))
            hexmac = ':'.join( [ "%02x" % ( x ) for x in reversed(device.mac) ] )
            settingsFile.set(device.hostname,'MACAddress',hexmac)
            settingsFile.set(device.hostname,'Device',hex(device.devtype))
            settingsFile.set(device.hostname,'Timeout',str(device.timeout))
            settingsFile.set(device.hostname,'Type',device.type.upper())
            print("\t\t%s: Found %s on %s (%s) type: %s" % (device.hostname, device.type, device.host, hexmac, hex(device.devtype)))
        settingsFile.write(ControlIniFile)
        ControlIniFile.close()
    except Exception as e:
        cprint ("Error writing settings file: %s" % e,"yellow")
        settings.restoreSettings()


#- The Type attribute is used to declare what sort of device we need to return
#- otherwise is only used by the device module (this one)

def readSettings(settingsFile,devname):
    try:
        Dev = devices.Dev[devname]
        if Dev['Type'] == 'RM' or Dev['Type'] == 'RM2':
            device = broadlink.rm((Dev['IPAddress'], 80), Dev['MACAddress'], Dev['Device'])
        elif Dev['Type'] == 'MP1':
            device = broadlink.mp1((Dev['IPAddress'], 80), Dev['MACAddress'], Dev['Device'])
        elif Dev['Type'] == 'SP1':
            device = broadlink.sp1((Dev['IPAddress'], 80), Dev['MACAddress'], Dev['Device'])
        elif Dev['Type'] == 'SP2':
            device = broadlink.sp2((Dev['IPAddress'], 80), Dev['MACAddress'], Dev['Device'])
        elif Dev['Type'] == 'A1':
            device = broadlink.a1((Dev['IPAddress'], 80), Dev['MACAddress'], Dev['Device'])
        elif Dev['Type'] == 'HYSEN':
            device = broadlink.hysen((Dev['IPAddress'], 80), Dev['MACAddress'], Dev['Device'])
        elif Dev['Type'] == 'S1C':
            device = broadlink.S1C((Dev['IPAddress'], 80), Dev['MACAddress'], Dev['Device'])
        elif Dev['Type'] == 'DOOYA':
            device = broadlink.dooya((Dev['IPAddress'], 80), Dev['MACAddress'], Dev['Device'])
        else:
            return False

        if 'Delay' in Dev:
            device.delay = Dev['Delay']
        else:
            device.delay = 0.0

        #- set the callbacks
        Dev['learnCommand'] = learnCommand
        Dev['sendCommand'] = sendCommand
        Dev['getStatus'] = None
        Dev['setStatus'] = None
        Dev['getSensor'] = getSensor
        Dev['BaseType'] = "broadlink"
        return device
    except Exception as e:
        cprint ("Broadlink device support requires broadlink python module.\npip3 install broadlink", "red")
        return None

def learnCommand(devname,device,params):
    try:
        device.enter_learning()
        start = time.time()
        #- We want the real device delay here, not the modified one
        #- min of 0.5 second.  Result is almost always 1 second
        sleeptime = max(devices.Dev[devname]["Delay"],0.5)
        LearnedCommand = None
        while LearnedCommand is None and time.time() - start < settings.GlobalTimeout:
            time.sleep(sleeptime)
            LearnedCommand = device.check_data()

        if LearnedCommand is None:
            cprint('Command not received',"yellow")
            return False

        AdditionalData = bytearray([0x00, 0x00, 0x00, 0x00])
        finalCommand = AdditionalData + LearnedCommand

        AESEncryption = AES.new(device.key, AES.MODE_CBC, bytes(device.iv))
        return binascii.hexlify(AESEncryption.decrypt(bytes(finalCommand)))
    except:
        traceback.print_exc()


def sendCommand(command,device,deviceName,params):
    se = params['command'] + ' side-effect'
    if command is False and se in params and params[se] is True:
        #- cprint ("Sorry, %s doesn't seem to be defined for your %s" % (params['command'],deviceName),"yellow")
        #- Silently ignore commands that are just used for side-effects
        return False
    try:
        decodedCommand = binascii.unhexlify(command)
        AESEncryption = AES.new(device.key, AES.MODE_CBC, bytes(device.iv))
        encodedCommand = AESEncryption.encrypt(bytes(decodedCommand))
        finalCommand = encodedCommand[0x04:]
    except Exception as e:
        if command is False:
            command = params['command']
            e = "command is undefined"
        cprint("broadlink sendCommand: %s to %s failed: %s" % (command,deviceName,e),"yellow")
        return False
    try:
        device.send_data(finalCommand)
        if 'deviceDelay' not in params:
            time.sleep(device.delay)
        else:
            time.sleep(float(params['deviceDelay']))
    except Exception as e:
        traceback.print_exc()
        cprint ("Probably timed out..","yellow")
        return False
    return True


#    def getStatus:

#    def setStatus:

def getSensor(device,deviceName,sensorName,params):
    Dev = devices.Dev[deviceName]
    try:
        # print ("Checking sensors %s %s" % (sensorName,deviceName))
        if "RM" in Dev['Type'].upper() and "temp" in sensorName:
            temperature = device.check_temperature()
            if temperature:
                if 'deviceDelay' not in params:
                    time.sleep(device.delay)
                else:
                    time.sleep(float(params['deviceDelay']))
                return temperature
        elif "A1" in Dev['Type'].upper():
            result = device.check_sensors()
            if result:
                if 'deviceDelay' not in params:
                    time.sleep(device.delay)
                else:
                    time.sleep(float(params['deviceDelay']))
                return result[sensorName]
        else:
            #cprint ("I don't know how to find %s for a %s" % (sensorName,Dev['Type']), "yellow")
            return False
    except Exception as e:
        cprint ("Error finding sensor %s in %s: %s" % (sensorName,deviceName,e),"yellow")
        traceback.print_exc()
    return False


devices.addDiscover(discover)
devices.addReadSettings(readSettings)




