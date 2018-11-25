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

    def discover(settingsFile,timeout,listen,broadcast):
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
            settingsFile.write(ControlIniFile)
            ControlIniFile.close()
        except Exception as e:
            cprint ("Error writing settings file: %s" % e,"yellow")
            settings.restoreSettings()


    def readSettings(devname):
        Dev = devices.Dev[devname]
        if Dev['Type'] == 'URL':
            device = type('', (), {})()
            device.url = Dev['URL']
        else:
            return False
        Dev['learnCommand'] = None
        Dev['sendCommand'] = sendCommand
        Dev['getStatus'] = None
        Dev['setStatus'] = None
        Dev['getSensor'] = None
        return device

#- Note that "command" is the decoded command.
#- The command name is found in params['command']
    def sendCommand(command,device,deviceName,params):
        try:
            if devices.Dev[deviceName]['Type'] == 'URL':
                URL = macros.expandVariables(device.url,params)
                PostData = json.dumps(params)
                r = requests.post(url = URL, data = PostData)
                cprint("%s/%s" % (deviceName,r.text),"green")
                time.sleep(float(params['deviceDelay']))
            return False
        except Exception as e:
            cprint("sendCommand: %s failed: %s" % (command,e),"yellow")
            return False


    devices.addDiscover(discover)
    devices.addReadSettings(readSettings)


except ImportError as e:
    cprint ("There was a problem importing the URL module: %s" % e, "red")

