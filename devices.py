import threading
import termcolor
from collections import defaultdict
import threadpool

global Dev
global DevList
global HomeDevice

#- LOGLEVEL
#- 0 = Special      3 = Events      6 = Debug
#- 1 = Errors       4 = Info
#- 2 = Warning      5 = Logs

LogLevel = 3
LogLevels = [ 'SPECIAL', 'ERROR', 'WARN', 'EVENT', 'INFO', 'LOG', 'DEBUG' ]
LogColors = [ 'magenta', 'red', 'yellow', 'blue', 'white', 'cyan', 'green' ]

DeviceByName = {}
DevList = []
Dev = defaultdict(dict)
Modlist = {}
DeviceByRoom = {}
CustomDash = False

FuncDiscover = []
FuncReadSettings = []
FuncShutdown = []
SettingsLock = threading.RLock()
OutputLock = threading.RLock()
LastThreadId = 0
LastLevel = 'INFO'
LastEnd = "\n"

def logfile(body,level='INFO',end="\n"):
    global LastThreadId
    global LastLevel
    global LastEnd
    with OutputLock:
        thread = threading.get_ident()
        if LogLevel >= LogLevels.index(level):
            try:
                if LastThreadId != thread or LastLevel != level:
                    if LastEnd != "\n":
                        print ("")
                LastThreadId = thread
                LastLevel = level
                LastEnd = end
            except Exception as e:
                pass
            termcolor.cprint(body,color=LogColors[LogLevels.index(level)],end=end)

def addDiscover(func):
    FuncDiscover.append(func)

def addReadSettings(func):
    FuncReadSettings.append(func)

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
    logfile("I don't know the type of device for %s" % devname,"ERROR")

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

def startUp(sock,addr,globalSet,globalGet,globalSend,handler):
    for dev in DeviceByName:
        if 'threads' in Dev[dev]:
            for i in range(1,Dev[dev]['threads']):
                threadpool.Thread(dev,sock,addr,handler,globalSend,globalGet,globalSet);
        else:
            threadpool.Thread(dev,sock,addr,handler,globalSend,globalGet,globalSet);

def shutDown(globalSet,globalGet):
    for func in FuncShutdown:
        func(globalSet,globalGet)

