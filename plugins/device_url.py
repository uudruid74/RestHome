import devices
from os import path
import settings
import threading
import macros
import traceback
import time
import json
import re
from devices import logfile

try:
    import requests
    from requests.exceptions import ConnectionError

    devices.Modlist['requests'] = True

except ImportError as e:
    pass

def discover(settingsFile,timeout,listen,broadcast):
    if 'requests' not in devices.Modlist:
        logfile ("URL/Webhook device support requires 'requests' python module.", "WARN")
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
        logfile ("Error writing settings file: %s" % e,"ERROR")
        settings.restoreSettings()


def readSettings(settingsFile,devname):
    Dev = devices.Dev[devname]
    if Dev['Type'] == 'URL':
        Dev['BaseType'] = "url"
        if 'requests' not in devices.Modlist:
            logfile ("URL/Webhook device support requires 'requests' python module.", "WARN")
            return False
        device = type('', (), {})()
        device.url = Dev['URL']
        if settingsFile.has_option(devname,"Method"):
            device.method = settingsFile.get(devname,"Method")
        else:
            device.method = "POST"
        if settingsFile.has_option(devname,"Find"):
            device.find = settingsFile.get(devname,"Find")
        if settingsFile.has_option(devname,"Set"):
            device.setvars = settingsFile.get(devname,"Set")
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
    Dev['virtualize'] = virtualize
    Dev['startup'] = startup
    return device

def virtualize(real):
    if 'Set' in real:
        del real['Set']
    if 'Find' in real:
        del real['Find']
    if 'Method' in real:
        del real['Method']
    return real

#- Note that "command" is the decoded command.
#- The command name is found in params['command']
def sendCommand(command,device,deviceName,params):
    try:
        if devices.Dev[deviceName]['Type'] == 'URL':
            URL = macros.expandVariables(device.url,params)
            #print ("Fetching " + URL)
            if device.method == "POST":
                headers = { 'Content-Type': 'application/json' }
                if 'value1' in params:
                    print ("value1 = %s" % params['value1'])
                r = requests.post(url=URL,json=params,headers=headers,timeout=4)
            else:
                r = requests.get(url=URL,data=params,timeout=4)
            if r.status_code != 200:
                if 'retries' not in params:
                    params['retries'] = 0
                if params["retries"] > 2:
                    logfile ("%s (Error %s): FAILED" % (params['command'],r.status_code),"WARN")
                    return False
                logfile ("%s (Error %s): Waiting 2s ..." % (params['command'],r.status_code),"ERROR")
                params["retries"] = params["retries"] + 1
                time.sleep(2)
                return sendCommand(command,device,deviceName,params)
            result = r.text
            if hasattr(device,'find'):
                #print ("Finding regex: %s" % device.find)
                regex = re.compile(device.find)
                match = regex.search(result,re.M)
                if match:
                    if hasattr(device,'setvars'):
                        for var in device.setvars.split():
                            globalSetStatus(var,match.group(var),params)
                    result = "FOUND: " + match.group()
                else:
                    result = "NOT FOUND.  Response: " + result[:40]
            logfile("  # %s/%s: %s" % (deviceName,params['command'],result[:60]),"DEBUG")
            time.sleep(float(params['deviceDelay']))
            return True
        return False
    except ConnectionError as e:
        if 'retries' not in params:
            params['retries'] = 0
        if params["retries"] > 2:
            print ("Retries Exceeded");
            raise # Not error we are looking for
        else:
            params["retries"] = params["retries"] + 1
            logfile ("CONNECTION ERROR(%s): Waiting 2s ..." % params['command'],"ERROR")
            time.sleep(2)
            return sendCommand(command,device,deviceName,params)
    except Exception as e:
        logfile("url sendCommand: %s to %s failed: %s" % (params['command'],deviceName,e),"ERROR")
#        traceback.print_exc()
        return False


def startup(setit,getit,sendit):
    global globalSetStatus
    globalSetStatus = setit


devices.addDiscover(discover)
devices.addReadSettings(readSettings)

