import threading
import termcolor
from collections import defaultdict
import threading

global Dev
global DevList
global HomeDevice

DeviceByName = {}
DevList = []
Dev = defaultdict(dict)
Modlist = {}
DeviceByRoom = {}
CustomDash = False

FuncDiscover = []
FuncReadSettings = []
FuncStartup = []
FuncShutdown = []
SettingsLock = threading.RLock()
LastThreadId = 0
LastColor = "grey"
LastEnd = "\n"

def cprint(body,color="grey",end="\n"):
    global LastThreadId
    global LastColor
    global LastEnd
    thread = threading.get_ident()
    try:
        if LastThreadId != thread or LastColor != color:
            if LastEnd != "\n":
                print ("")
    except Exception as e:
        pass
    LastThreadId = thread
    LastColor = color
    LastEnd = end
    termcolor.cprint(body,color=color,end=end)

def addDiscover(func):
    FuncDiscover.append(func)

def addReadSettings(func):
    FuncReadSettings.append(func)

def addStartup(func):
    FuncStartup.append(func)

def addShutdown(func):
    FuncShutdown.append(func)

def addRoom(device,name):
    if name in DeviceByRoom:
        DeviceByRoom[name] = DeviceByRoom[name] + " " + device
    else:
        DeviceByRoom[name] = device

def setHome(device):
    DeviceByRoom['House'] = device

def getHome():
    if 'House' in DeviceByRoom:
        return DeviceByRoom['House']
    return Dev['default']

def setDash(html):
    global CustomDash
    CustomDash = html

def getDash():
    return CustomDash

def discover (settings,timeout,listen,broadcast):
    for func in FuncDiscover:
        #- TODO: Thread this
        func(settings,timeout,listen,broadcast)

def readSettings (settings,devname):
    for func in FuncReadSettings:
        #- TODO: Refactor and thread
        retvalue = func(settings,devname)
        if retvalue is not False:
            return retvalue
    cprint ("I don't know the type of device for %s" % devname,"yellow")

def dumpDevices():
    retval = '''{\n\t"ok": "deviceList"'''
    with SettingsLock:
        for devicename,info in Dev.items():
            if 'Comment' not in info:
                comment = 'Unknown'
            else:
                comment = info['Comment']
            retval += ''',\n\t"%s": "%s"''' % (devicename, comment)
    retval += '''\n}'''
    return retval

def dumpRooms():
    retval = '''{\n\t"ok": "%s"''' % DeviceByRoom['House']
    Room = {}
    with SettingsLock:
        for roomname,devicelist in DeviceByRoom.items():
            if roomname == 'House':
                continue
            retval += ''',\n\t"%s": "%s"''' % (roomname,devicelist)
    retval += '''\n}'''
    return retval

#- These commands work as follows
#- The startup callback below is sent to all devices that want it
#- Any "StartupCommand" registered in the settings file is done next
#- During a reload or shutdown, a "Shutdown" command is sent before
#- the 20 second shutdown delay.
#- On a reload, the startup callback is done again, as is any
#- StartupCommand.  
#- Only on final shutdown is the shutdown callback made

def startUp(globalSet,globalGet,globalSend):
    for func in FuncStartup:
        func(globalSet,globalGet,globalSend)

def shutDown(globalSet,globalGet):
    for func in FuncShutdown:
        func(globalSet,globalGet)

