from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import broadlink, configparser
import sys, getopt
import time, binascii
import netaddr
import settings
import signal
import socket
import errno
import json
import shutil
import macros
import re
import collections
from os import path
from Crypto.Cipher import AES

class Server(HTTPServer):
    def get_request(self):
        result = None
        while result is None:
            try:
                result = self.socket.accept()
                result[0].setblocking(0)
                result[0].settimeout(self.timeout)
            except socket.timeout:
                pass
        return result

    def server_bind(self):
        HTTPServer.server_bind(self)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class Handler(BaseHTTPRequestHandler):
    Parameters = collections.defaultdict(lambda : ' ')
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()

    def handle(self):
        self.close_connection = 0

        while not self.close_connection:
            try:
                self.handle_one_request()
            except IOError as e:
                if e.errno == errno.EWOULDBLOCK:
                    self.close_connection=1

    def do_GET(self):
        try:
            if GlobalPassword:
                try:
                    if RestrictAccess and self.client_address[0] not in RestrictAccess:
                        return self.access_denied()
                    return self.messageHandler()
                except NameError as e:
                    print ("Error: %s" % e)
                    self.password_required()
        except NameError:                   #- No security specified
            self.messageHandler()

    def do_POST(self):
        password = ''
        try:
            content_len = int(self.headers.getheader('content-length', 0))
            self.Parameters.update(json.loads(self.rfile.read(content_len)))
            password = self.Parameters['password'];
        except:
            pass
        try:
            if GlobalPassword and GlobalPassword == password:
                return self.messageHandler()
            else:
                print ("TRY %s != %s" % (GlobalPassword, password))
        except NameError:
                return self.password_required()
        print ("LSE %s != %s" % (GlobalPassword, self.Parameters['password']))
        self.password_required()

    def password_required(self):
        response = "Password required from %s" % self.client_address[0]
        self.wfile.write('''{ "error": "%s" }''' % response)
        print (response)
        self.close_connection = 1
        return False

    def access_denied(self):
        response = "Client %s is not allowed!" % self.client_address[0]
        self.wfile.write('''{ "error": "%s" }''' % response)
        print (response)
        self.close_connection = 1
        return False

    def messageHandler(self):
        if 'favicon' in self.path:
            return False

        self._set_headers()
        if '?' in self.path:
            (self.path,query) = self.path.split('?')
            params = re.split('[&=]+',query)
            for index in xrange(0,len(params),2):
                self.Parameters[params[index]] = params[index+1]
        paths = re.split('[//=]+',self.path)
        if 'learnCommand' in self.path:
            try:
                if self.client_address[0] not in LearnFrom:
                    print ("Won't learn commands from %s.  Access Denied!" % self.client_address[0])
                    return False
            except NameError:
                pass

            if paths[2] == 'learnCommand':
                deviceName = paths[1]
                commandName = paths[3]
            else:
                commandName = paths[2]
                deviceName = None
            result = learnCommand(commandName,self.Parameters,deviceName)
            if result == False:
                response = "Failed: No command learned"
            else:
                response = "Learned: %s" % commandName

        elif 'sendCommand' in self.path:
            if paths[2] == 'sendCommand':
                deviceName = paths[1]
                commandName = paths[3]
            else:
                commandName = paths[2]
                deviceName = None
            if 'on' in commandName or 'off' in commandName:
                status = commandName.rsplit('o', 1)[1]
                realcommandName = commandName.rsplit('o', 1)[0]
                print(status, realcommandName)
                if 'n' in status:
                    result = setStatus(realcommandName, '1',self.Parameters,deviceName)
                elif 'ff' in status:
                    result = setStatus(realcommandName, '0',self.Parameters,deviceName)
                if result:
                    result = '''{ "%s": "%s" }''' % (realcommandName,result)
            else:
                result = sendCommand(commandName, self.Parameters, deviceName)
                print ("SendCommand result: %s" % result)
            if result == False:
                response = "Failed: Unknown command"
            else:
                response = result

        elif 'getStatus' in self.path:
            if paths[2] == 'getStatus':
                commandName = paths[3]
                deviceName = paths[1]
            else:
                commandName = paths[2]
                deviceName = None

            status = getStatus(commandName,deviceName)
            if (status):
                response = '''{ "%s": "%s" }''' % (commandName,status)
            else:
                response = "Failed: Unknown command"

        elif 'setStatus' in self.path:
            if paths[2] == 'setStatus':
                commandName = paths[3]
                deviceName = paths[1]
                status = paths[4]
            else:
                commandName = paths[2]
                deviceName = None
                status = paths[3]
            result = setStatus(commandName, status, self.Parameters, deviceName)
            if (result):
                response = '''{ "%s": "%s" }''' % (commandName, result)
            else:
                response = "Failed: Unknown command"

        elif 'toggleStatus' in self.path:
            if paths[2] == 'toggleStatus':
                commandName = paths[3]
                deviceName = paths[1]
            else:
                commandName = paths[2]
                deviceName = None
            status = toggleStatus(commandName, self.Parameters, deviceName)
            if (status):
                response = '''{ "%s": "%s" }''' % (commandName, status)
            else:
                response = "Failed: Unknown command"

        elif 'getSensor' in self.path or 'a1' in self.path:
            if paths[2] == 'getSensor':
                sensor = paths[3]
                deviceName = paths[1]
            else:
                sensor = paths[2]
                deviceName = None
                #- Old syntax - find a compatible device
                if "A1" == paths[2].upper()[:2]:
                    for dev in devices:
                        if "A1" == dev.type.upper():
                            deviceName = dev.hostname
                            break
            result = getSensor(sensor, self.Parameters, deviceName)
            if result == False:
                reponse = "Failed to get data"
            else:
                if sensor == 'temperature' or sensor == 'humidity':
                    response = '''{ "%s": %s }''' % (sensor, result)
                else:
                    response = '''{ "%s": "%s" }''' % (sensor, result)
        else:
            response = "Failed"
        if "Failed" in response or "error" in response:
            self.wfile.write('''{ "error": "%s" }''' % response)
        elif response.startswith('{'):
            self.wfile.write(response)
        else:
            self.wfile.write('''{ "ok": "%s" }''' % response)
        print ("\t"+response)
        print ""

def sendCommand(commandName,params,deviceName):
    if deviceName == None:
        device = devices[0]
        serviceName = 'Commands'
    elif deviceName in DeviceByName:
        device = DeviceByName[deviceName];
        serviceName = deviceName + ' Commands'
    else:
        return "Failed: No such device, %s" % deviceName

    print ("sendCommand: %s Orig: %s" % (commandName,deviceName))
    origCommand = commandName
    if commandName.strip() != '':
        result = macros.checkConditionals(commandName,params,deviceName)
        print ("checkCond result: %s = %s" % (commandName,result))
        if result:
            return result
        if settingsFile.has_option(serviceName, commandName):
            commandName = settingsFile.get(serviceName, commandName)
        elif settingsFile.has_option('Commands', commandName):
            commandName = settingsFile.get('Commands', commandName)

        result = macros.checkMacros(commandName,params,deviceName)
        print ("Macro Result: %s = %s" % (commandName,result))
        if result:
            return result

        try:
            deviceKey = device.key
            deviceIV = device.iv

            decodedCommand = binascii.unhexlify(commandName)
            AESEncryption = AES.new(str(deviceKey), AES.MODE_CBC, str(deviceIV))
            encodedCommand = AESEncryption.encrypt(str(decodedCommand))

            finalCommand = encodedCommand[0x04:]
        except:
            return False    #- No such command

        try:
            device.send_data(finalCommand)
        except Exception:
            return "Probably timed out.."
        return origCommand
    else:
        return False

def learnCommand(commandName, params, deviceName=None):
    if deviceName == None:
        device = devices[0]
        sectionName = 'Commands'
    elif deviceName in DeviceByName:
        device = DeviceByName[deviceName];
        sectionName = deviceName + ' Commands'
    else:
        return "Failed: No such device, %s" % deviceName

    if OverwriteProtected and settingsFile.has_option(sectionName,commandName):
        print ("Command %s alreadyExists and changes are protected!" % commandName)
        return False

    print ("Waiting %d seconds to capture command" % GlobalTimeout)

    deviceKey = device.key
    deviceIV = device.iv

    device.enter_learning()
    time.sleep(GlobalTimeout)
    LearnedCommand = device.check_data()

    if LearnedCommand is None:
        print('Command not received')
        return False

    AdditionalData = bytearray([0x00, 0x00, 0x00, 0x00])
    finalCommand = AdditionalData + LearnedCommand

    AESEncryption = AES.new(str(deviceKey), AES.MODE_CBC, str(deviceIV))
    decodedCommand = binascii.hexlify(AESEncryption.decrypt(str(finalCommand)))

    backupSettings()
    try:
        broadlinkControlIniFile = open(path.join(settings.applicationDir, 'settings.ini'), 'w')
        if not settingsFile.has_section(sectionName):
            settingsFile.add_section(sectionName)
        settingsFile.set(sectionName, commandName, decodedCommand)
        settingsFile.write(broadlinkControlIniFile)
        broadlinkControlIniFile.close()
        return commandName
    except StandardError as e:
        print("Error writing settings file: %s" % e)
        restoreSettings()
        return False

def setStatus(commandName, status, params, deviceName=None):
    if deviceName == None:
        sectionName = 'Status'
    else:
        sectionName = deviceName + ' Status'

    backupSettings()
    try:
        if not settingsFile.has_section(sectionName):
            settingsFile.add_section(sectionName)
        broadlinkControlIniFile = open(path.join(settings.applicationDir, 'settings.ini'), 'w')
        settingsFile.set(sectionName, commandName, status)
        settingsFile.write(broadlinkControlIniFile)
        broadlinkControlIniFile.close()
        if settingsFile.has_section("SET "+commandName):
            if settingsFile.has_option("SET "+commandName, "trigger"):
                rawcommand = settingsFile.get("SET "+commandName, "trigger")
                print ("Trigger = %s" % rawcommand)
                return sendCommand(rawcommand,params,deviceName)
            else:
                print("SET %s: A trigger is required" + commandName)
        return getStatus(commandName,params,deviceName)
    except StandardError as e:
        print ("Error writing settings file: %s" % e)
        restoreSettings()
        return False

def getStatus(commandName, params, deviceName=None):
    if deviceName == None:
        sectionName = 'Status'
    else:
        sectionName = deviceName + ' Status'

    if settingsFile.has_option(sectionName,commandName):
        status = settingsFile.get(sectionName, commandName)
        return status
    status = getSensor(commandName,params,deviceName)
    if status:
        return status
    else:
        print ("Can't find %s %s" % (sectionName, commandName))
        return False

def toggleStatus(commandName, params, deviceName=None):
    print (deviceName)
    status = getStatus(commandName,params,deviceName)
    print ("Status = %s" % status)
    try:
        if status == "0":
            return setStatus(commandName,"1",params,deviceName)
    except:
        pass
    return setStatus(commandName,"0",params,deviceName)

def getSensor(sensorName,params,deviceName=None):
    if deviceName == None:
        device = devices[0]
    elif deviceName in DeviceByName:
        device = DeviceByName[deviceName]
    else:
        return "Failed: No such device, %s" % deviceName

    try:
        print ("Checking sensors %s %s" % (sensorName,deviceName))
        if "RM" in device.type.upper() and "temp" in sensorName:
            temperature = device.check_temperature()
            if temperature:
                return temperature
        if "A1" in device.type.upper():
            result = device.check_sensors()
            if result:
                return result[sensorName]
    except:
        pass    #- Ignore errors and just return false
    return False

def start(server_class=Server, handler_class=Handler, port=8080, listen='0.0.0.0', timeout=1):
    server_address = (listen, port)
    httpd = server_class(server_address, handler_class)
    httpd.timeout = timeout
    print ('\nStarting broadlink-rest server on %s:%s ...' % (listen,port))
    while not InterruptRequested:
        httpd.handle_request()

def backupSettings():
    shutil.copy2(settings.settingsINI,settings.settingsINI+".bak")

def restoreSettings():
    if path.isfile(settings.settingsINI+".bak"):
        shutil.copy2(settings.settingsINI+".bak",settings.settingsINI)
    else:
        print ("Can't find backup to restore!  Refusing to make this worse!")
        sys.exit()

def readSettingsFile():
    global devices
    global DeviceByName
    global RestrictAccess
    global LearnFrom
    global OverwriteProtected
    global GlobalPassword
    global GlobalTimeout
    global settingsFile

    # A few defaults
    serverPort = 8080
    Autodetect = False
    OverwriteProtected = True
    listen_address = '0.0.0.0'
    broadcast_address = '255.255.255.255'

    settingsFile = configparser.ConfigParser()
    settingsFile.optionxform = str
    settingsFile.read(settings.settingsINI)

    Dev = settings.Dev
    GlobalTimeout = settings.GlobalTimeout
    DiscoverTimeout = settings.DiscoverTimeout

    # Override them
    if settingsFile.has_option('General', 'password'):
        GlobalPassword = settingsFile.get('General', 'password').strip()

    if settingsFile.has_option('General', 'serverPort'):
        serverPort = int(settingsFile.get('General', 'serverPort'))

    if settingsFile.has_option('General','serverAddress'):
        listen_address = settingsFile.get('General', 'serverAddress')
        if listen_address.strip() == '':
            listen_address = '0.0.0.0'

    if settingsFile.has_option('General', 'restrictAccess'):
        RestrictAccess = settingsFile.get('General', 'restrictAccess').strip()

    if settingsFile.has_option('General', 'learnFrom'):
        LearnFrom = settingsFile.get('General', 'learnFrom').strip();

    if settingsFile.has_option('General', 'allowOverwrite'):
        OverwriteProtected = False

    if settingsFile.has_option('General','broadcastAddress'):
        broadcast = settingsFile.get('General', 'broadcastAddress')
        if broadcast_address.strip() == '':
            broadcast_address = '255.255.255.255'

    if settingsFile.has_option('General', 'Autodetect'):
        try:
            DiscoverTimeout = int(settingsFile.get('General', 'Autodetect').strip())
        except:
            DiscoverTimeout = 5
        Autodetect = True
        settingsFile.remove_option('General','Autodetect')

    # Device list
    DeviceByName = {}
    if not settings.DevList:
        Autodetect = True

    if Autodetect == True:
        print ("Beginning device auto-detection ... ")
        # Try to support multi-homed broadcast better
        try:
            devices = broadlink.discover(DiscoverTimeout,listen_address,broadcast_address)
        except:
            devices = broadlink.discover(DiscoverTimeout,listen_address)

        backupSettings()
        try:
            broadlinkControlIniFile = open(path.join(settings.applicationDir, 'settings.ini'), 'w')
            for device in devices:
                try:
                    device.hostname = socket.gethostbyaddr(device.host[0])[0]
                    if "." in device.hostname:
                        device.hostname = device.hostname.split('.')[0]
                except:
                    device.hostname = "Broadlink" + device.type.upper()
                if device.hostname in DeviceByName:
                    device.hostname = "%s-%s" % (device.hostname, str(device.host).split('.')[3])
                DeviceByName[device.hostname] = device
                if not settingsFile.has_section(device.hostname):
                    settingsFile.add_section(device.hostname)
                settingsFile.set(device.hostname,'IPAddress',str(device.host[0]))
                hexmac = ':'.join( [ "%02x" % ( x ) for x in reversed(device.mac) ] )
                settingsFile.set(device.hostname,'MACAddress',hexmac)
                settingsFile.set(device.hostname,'Device',hex(device.devtype))
                settingsFile.set(device.hostname,'Timeout',str(device.timeout))
                settingsFile.set(device.hostname,'Type',device.type.upper())
                device.auth()
                print ("%s: Found %s on %s (%s) type: %s" % (device.hostname, device.type, device.host, hexmac, hex(device.devtype)))
            settingsFile.write(broadlinkControlIniFile)
            broadlinkControlIniFile.close()
        except StandardError as e:
            print ("Error writing settings file: %s" % e)
            restoreSettings()
    else:
        devices = []
    if settings.DevList:
        for devname in settings.DevList:
            if Dev[devname,'Type'] == 'RM' or Dev[devname,'Type'] == 'RM2':
                device = broadlink.rm((Dev[devname,'IPAddress'], 80), Dev[devname,'MACAddress'], Dev[devname,'Device'])
            if Dev[devname,'Type'] == 'MP1':
                device = broadlink.mp1((Dev[devname,'IPAddress'], 80), Dev[devname,'MACAddress'], Dev[devname,'Device'])
            if Dev[devname,'Type'] == 'SP1':
                device = broadlink.sp1((Dev[devname,'IPAddress'], 80), Dev[devname,'MACAddress'], Dev[devname,'Device'])
            if Dev[devname,'Type'] == 'SP2':
                device = broadlink.sp2((Dev[devname,'IPAddress'], 80), Dev[devname,'MACAddress'], Dev[devname,'Device'])
            if Dev[devname,'Type'] == 'A1':
                device = broadlink.a1((Dev[devname,'IPAddress'], 80), Dev[devname,'MACAddress'], Dev[devname,'Device'])
            if Dev[devname,'Type'] == 'HYSEN':
                device = broadlink.hysen((Dev[devname,'IPAddress'], 80), Dev[devname,'MACAddress'], Dev[devname,'Device'])
            if Dev[devname,'Type'] == 'S1C':
                device = broadlink.S1C((Dev[devname,'IPAddress'], 80), Dev[devname,'MACAddress'], Dev[devname,'Device'])
            if Dev[devname,'Type'] == 'DOOYA':
                device = broadlink.dooya((Dev[devname,'IPAddress'], 80), Dev[devname,'MACAddress'], Dev[devname,'Device'])
            device.timeout = Dev[devname,'Timeout']
            if not devname in DeviceByName:
                device.hostname = devname
                device.auth()
                devices.append(device)
                print ("%s: Read %s on %s (%s)" % (devname, device.type, str(device.host[0]), device.mac))
            DeviceByName[devname] = device
    return { "port": serverPort, "listen": listen_address, "timeout": GlobalTimeout }

def SigUsr1(signum, frame):
    print ("\nReloading configuration ...")
    global InterruptRequested
    InterruptRequested = True

def SigInt(signum, frame):
    print ("\nShuting down server ...")
    global ShutdownRequested
    global InterruptRequested
    ShutdownRequested = True
    InterruptRequested = True

if __name__ == "__main__":
    global ShutdownRequested
    global InteruptRequested
    ShutdownRequested = False
    signal.signal(signal.SIGUSR1,SigUsr1)
    signal.signal(signal.SIGINT,SigInt)
    while not ShutdownRequested:
        serverParams = readSettingsFile()
        InterruptRequested = False
        macros.init_callbacks(settingsFile,sendCommand,getStatus,setStatus)
        start(**serverParams)
        if not ShutdownRequested:
            reload(settings)
