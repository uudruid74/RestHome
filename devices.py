import threading
from termcolor import cprint
from collections import defaultdict

global Dev
global DevList

DeviceByName = {}
DevList = []
Dev = defaultdict(dict)
Modlist = {}

FuncDiscover = []
FuncReadSettings = []
FuncStartup = []
FuncShutdown = []
SettingsLock = threading.RLock()

def addDiscover(func):
    FuncDiscover.append(func)

def addReadSettings(func):
    FuncReadSettings.append(func)

def addStartup(func):
    FuncStartUp.append(func)

def addShutdown(func):
    FuncShutDown.append(func)

def discover (settings,timeout,listen,broadcast):
    for func in FuncDiscover:
        func(settings,timeout,listen,broadcast)

def readSettings (settings,devname):
    for func in FuncReadSettings:
        retvalue = func(settings,devname)
        if retvalue is not False:
            return retvalue
    cprint ("I don't know the type of device for %s" % devname,"yellow")

def dumpDevices():
    retval = '''{\n\t"ok": "deviceList"\n'''
    with SettingsLock:
        for devicename,info in Dev.items():
            if 'Comment' not in info:
                comment = 'Unknown'
            else:
                comment = info['Comment']
            retval += '''\t"%s": "%s"\n''' % (devicename, comment)
    retval += '''}'''
    return retval

def startUp():
    for func in FuncStartup:
        func()

def shutDown():
    for func in FuncShutdown:
        func()

