from termcolor import cprint
from collections import defaultdict

global Dev
global DevList

DeviceByName = {}
DevList = []
Dev = defaultdict(dict)

FuncDiscover = []
FuncReadSettings = []
FuncStartup = []
FuncShutdown = []

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

def readSettings (devname):
    for func in FuncReadSettings:
        retvalue = func(devname)
        if retvalue is not False:
            return retvalue
    cprint ("I don't know the type of device for %s" % devname,"yellow")

def startUp():
    for func in FuncStartup:
        func()

def shutDown():
    for func in FuncShutdown:
        func()

