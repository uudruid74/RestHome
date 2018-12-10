import devices
from termcolor import cprint
from os import path
import settings
import threading
import macros
import traceback
import time
import json

try:
    import requests

    devices.Modlist['requests'] = True

except ImportError as e:
    pass

def discover(settingsFile,timeout,listen,broadcast):
    if 'requests' not in devices.Modlist:
        cprint ("URL/Webhook device support requires 'requests' python module.", "red")
        return False

    default = "IFTTT"
    if settingsFile.has_section(default):
        return
    print ("\tConfiguring default URL device, IFTTT ...")

    settings.backupSettings()
    try:
        ControlIniFile = open(path.join(settings.applicationDir, 'settings.ini'), 'w')
        settingsFile.add_section(default)
        settingsFile.add_section(default + ' Status')
        URL = '''https://maker.ifttt.com/trigger/$command/with/key/$status(API_KEY)'''
        API_KEY = '''Click 'Documentation' from https://ifttt.com/maker_webhooks to get API Key'''
        settingsFile.set(default,'URL',URL)
        settingsFile.set(default + ' Status','API_KEY',API_KEY)
        settingsFile.set(default,'Type','URL')
        settingsFile.set(default,'skipRepeats','False')
        settingsFile.write(ControlIniFile)
        ControlIniFile.close()
    except Exception as e:
        cprint ("Error writing settings file: %s" % e,"yellow")
        settings.restoreSettings()


def readSettings(devname):
    Dev = devices.Dev[devname]
    if Dev['Type'] == 'URL':
        if 'requests' not in devices.Modlist:
            cprint ("URL/Webhook device support requires 'requests' python module.", "red")
            return False
        device = type('', (), {})()
        device.url = Dev['URL']
    else:
        return False
    if 'Delay' in Dev:
        device.delay = Dev['Delay']
    else:
        device.delay = 0.25     #- Otherwise you get a Bad Gateway error from IFTTT

    Dev['learnCommand'] = None
    Dev['sendCommand'] = sendCommand
    Dev['getStatus'] = None
    Dev['setStatus'] = None
    Dev['getSensor'] = None
    Dev['BaseType'] = "url"
    return device

#- Note that "command" is the decoded command.
#- The command name is found in params['command']
def sendCommand(command,device,deviceName,params):
    try:
        if devices.Dev[deviceName]['Type'] == 'URL':
            URL = macros.expandVariables(device.url,params)
            PostData = json.dumps(params)
            r = requests.post(url = URL, data = PostData)
            cprint("%s/%s-%s" % (deviceName,params['command'],r.text),"green")
            time.sleep(float(params['deviceDelay']))
            return True
        return False
    except Exception as e:
        cprint("url sendCommand: %s to %s failed: %s" % (params['command'],deviceName,e),"yellow")
        traceback.print_exc()
        return False


devices.addDiscover(discover)
devices.addReadSettings(readSettings)

