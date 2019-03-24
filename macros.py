import wol
import string
import time
import re
from platform import system as system_name
from math import ceil as ceiling
import subprocess
import json
import threading
import sys
import traceback
import devices

def append(a,b):
    if a.strip() == '':
        return b
    else:
        return ' '.join([a,b])

class EventNode(object):
    def __init__(self,name="timer",fire=1,command="PRINT No Command",params=None):
        self.name = name
        self.created = time.time()
        self.timestamp = self.created + fire
        self.command = command
        self.params = params
        self.nextNode = None

class EventList(object):
    def __init__(self):
        self.begin = None
        self.lock = threading.RLock()
    def nextEvent(self):
        with self.lock:
            if self.begin != None:
                y = self.begin.timestamp - time.time()
                return y
            else:
                return 86400 #- 1 day
    def insert(self,node):
        #print ("Insert %s = %s" % (node.name,node.command))
        with self.lock:
            node.nextNode = self.begin
            #- insert into beginning
            if self.begin == None or node.timestamp < node.nextNode.timestamp:
                self.begin = node
                return
            #- insert into middle
            last = pointer = self.begin
            while pointer != None:
                if node.timestamp >= pointer.timestamp:
                    last = pointer
                    pointer = pointer.nextNode
                else:
                    last.nextNode = node
                    node.nextNode = pointer
                    return
            #- insert at end
            last.nextNode = node
            node.nextNode = None
    def pop(self):
        with self.lock:
            retvalue = self.begin
            if retvalue is not None and retvalue.nextNode is not None:
                self.begin = retvalue.nextNode
            else:
                self.begin = None
            return retvalue
    def add(self,name,fire,command,params):
        with self.lock:
            found = self.find(name)
            if found:
                #devices.logfile("Deleting old event: %s=%s" % (found.name,found.command),"ERROR")
                ret = self.delete(name)
            newparams = params.copy()
            newparams['serialize'] = True
            self.insert(EventNode(name,fire,command,newparams))
    def find(self,name):
        with self.lock:
            node = self.begin
            while node != None:
                if node.name == name:
                    return node
                else:
                    node = node.nextNode
            return None
    def deleteAll(self,name):
        with self.lock:
            node = self.begin
            if node == None:
                return None
            while node.name.startswith(name):
                node = node.nextNode
                self.begin = node
            while node.nextNode != None:
                if node.nextNode.name.startswith(name):
                    found = node.nextNode
                    node.nextNode = found.nextNode
                node = node.nextNode
            return None
    def delete(self,name):
        with self.lock:
            node = self.begin
            if node == None:
                return None
            if node.name == name:
                self.begin = node.nextNode
                return node
            while node.nextNode != None:
                if node.nextNode.name == name:
                    found = node.nextNode
                    node.nextNode = found.nextNode
                    return found
                else:
                    node = node.nextNode
            return None
    def dump(self):
        now = time.time()
        retval = '''{\n\t"ok": "eventList"'''
        with self.lock:
            node = self.begin
            while node != None:
                retval += ''',\n\t"%s": "%s"''' % (int(node.timestamp - now), node.name + " = " + node.command)
                node = node.nextNode
        retval += '''\n}'''
        return retval

eventList = EventList()

#-
#- TODO - allow $default(var), just like $status, only a param can override the value
#-
def expandVariables(commandString,query):
    statusVar = commandString.find("$status(")
    newquery = query.copy()
    while statusVar > -1:
        endVar = commandString.find(")",statusVar)
        if endVar < 0:
            devices.logfile ("No END Parenthesis found in $status variable","ERROR")
            statusVar = -1
        varname = commandString[statusVar+8:endVar]
        varvalue = getStatus(varname,newquery)
        commandString = commandString.replace(commandString[statusVar:endVar+1],varvalue)
        statusVar = commandString.find("$status(")
    firstPass = commandString
    secondPass = string.Template(firstPass).substitute(newquery)
    return secondPass

#- parenSplit divides up a line into separate commands, keeping parenthesis 
def parenSplit(parenstring):
    found = []
    first = ccount = nesting = 0
    for c in parenstring:
        ccount+=1
        if c == '(':
            nesting += 1;
        if c == ')':
            nesting -= 1;
            if nesting < 0:
                devices.logfile("Malformed command - parenthesis don't match at %s: %s" % (ccount,parenstring))
            elif nesting == 0:
                #- found substring
                if ccount+1 < len(parenstring):
                    if parenstring[ccount+1:].find(' ') != -1:
                        ccount += parenstring[ccount+1:].find(' ')
                        found.append(parenstring[first:ccount])
                        first = ccount+1
                    else:
                        found.append(parenstring[first:])
                        return found
    if first < len(parenstring):
        found.append(parenstring[first:])
    return found


def relayTo(device,query):
    if device == query['device']:
        devices.logfile ("RELAY %s attempted to relay to itself" % query['command'],"ERROR")
        return True
    newquery = query.copy()
    newquery['device'] = device
    #print ("Relaying %s to %s" % (query['command'],device))
    sendCommand(query['command'],newquery)
    return

def mathOp(dest,op,val1,val2,query):
    try:
        val1 = int(val1.strip())
    except:
        val1 = 0
    try:
        val2 = int(val2.strip())
    except:
        val2 = 0
    if op == "+":
        amount = val1 + val2
    elif op == "-":
        amount = val1 - val2
    elif op == "/":
        amount = val1 / val2
    elif op == "*":
        amount = val1 * val2
    #print ("New amount is %s from %s %s %s" % (amount,val1,op,val2))
    result = setStatus(dest,str(amount),query)
    return result

def incrementVar(variable,amount,query):
    return mathOp(variable,"+",getStatus(variable,query),amount,query)

def decrementVar(variable,amount,query):
    return mathOp(variable,"-",getStatus(variable,query),amount,query)

def cancelEvent(variable):
    eventList.delete(variable)
    return

#- return True if it's a MACRO = stops execution of command!
def checkMacros(OcommandFromSettings,query):
    #print ("checkMacros: %s" % OcommandFromSettings)
    if OcommandFromSettings.startswith('.'):
        commandFromSettings = OcommandFromSettings[1:]
    elif OcommandFromSettings.startswith('MACRO'):
        commandFromSettings = OcommandFromSettings
    else:
        return False

    if commandFromSettings.startswith("PRINT "):
        devices.logfile ("  > "+expandVariables(commandFromSettings[6:],query),"INFO")
        return True
    elif commandFromSettings == "NOP" or commandFromSettings.startswith("#"):
        return True
    elif commandFromSettings.startswith("SH "):
        shellCommand(expandVariables(commandFromSettings[3:].strip(),query))
        return True
    elif commandFromSettings.startswith("!"):
        shellCommand(expandVariables(commandFromSettings[1:].strip(),query))
        return True
    elif commandFromSettings.startswith("SET "):
        setStatus(commandFromSettings[4:],"1",query)
        return True
    elif commandFromSettings.startswith("INC "):
        params = commandFromSettings[4:].split()
        incrementVar(params[0],params[1],query)
        return True
    elif commandFromSettings.startswith("CANCEL "):
        variable = int(getStatus(commandFromSettings[7:],query))
        cancelEvent(variable)
        return True
    elif commandFromSettings.startswith("DEC "):
        params = commandFromSettings[4:].split()
        decrementVar(params[0],params[1],query)
        return True
    elif commandFromSettings.startswith("CLEAR "):
        setStatus(commandFromSettings[6:],"0",query)
        return True
    elif commandFromSettings.startswith("TOGGLE "):
        toggleStatus(commandFromSettings[7:],query)
        return True
    elif commandFromSettings.startswith("RELAY "):
        device = commandFromSettings[6:].strip()
        relayTo(device,query)
        return True
    elif commandFromSettings.startswith("->"):
        device = commandFromSettings[2:].strip()
        relayTo(device,query)
        return True
    elif commandFromSettings.startswith("MACRO ") or OcommandFromSettings.startswith(".") or '(' in commandFromSettings:
        if 'serialize' in query and query['serialize']:
            #print ("Executing %s" % commandFromSettings)
            deviceName = query["device"]
            with devices.Dev[deviceName]['Lock']:
                exec_macro(commandFromSettings,query)
        else:
            devices.logfile("Making Event for %s" % commandFromSettings,"LOG")
            eventName = query['command'];
            if eventName.endswith('on'):
                eventName = eventName[:-2]
            elif eventName.endswith('off'):
                eventName = eventName[:-3]
            eventList.add(eventName,query["deviceDelay"],OcommandFromSettings,query)
        return True
    else:
        return False #- not a macro


def exec_macro(commandFromSettings,query):
    #print ("exec_macro: %s" % commandFromSettings)
    if commandFromSettings.startswith("MACRO "):
        expandedCommand = expandVariables(commandFromSettings[6:],query)
    elif commandFromSettings.startswith("."):
        expandedCommand = expandVariables(commandFromSettings[1:],query)
    else:
        expandedCommand = expandVariables(commandFromSettings,query)
    commandFromSettings = expandedCommand.strip()
    for command in commandFromSettings.split():
        newquery = query.copy()
        devices.logfile (command,"LOG",end=' ')
        sys.stdout.flush()

        if command == "sleep":
            time.sleep(1)
            continue

        if "(" in command:
            timerCount = 0
            repeat = 1
            for command in parenSplit(command):
                if command[command.rfind(")"):].find(",") != -1:
                    repeat = int(command[command.rfind(",")+1:])
                    #print ("Repeating %s times" % repeat)
                paramString = command[command.find("(")+1:command.rfind(")")]
                command = command[:command.find("(")]
                if command == "set":
                    #print ("SET called on %s" % paramString)
                    if ',' in paramString:
                        (paramString,value) = paramString.split(',')
                    else:
                        value = "1"
                    setStatus(paramString,value,newquery)
                elif command == "clear":
                    setStatus(paramString,"0",newquery)
                elif command == "sleep":
                    for count in range(0,repeat):
                        time.sleep(float(paramString))
                elif command == "toggle":
                    if getStatus(paramString,query) == "0":
                        setStatus(paramString,"1",newquery)
                    else:
                        setStatus(paramString,"0",newquery)
                #- min/max function is ...
                #- getmyval = .min(hello,23,45,12)
                #- getmyval would set "hello" to 12
                elif command == "min":
                    params = paramString.split(',')
                    varname = params.pop(0)
                    setStatus(varname,str(min(params)),newquery)
                elif command == "max":
                    params = paramString.split(',')
                    varname = params.pop(0)
                    setStatus(varname,str(max(params)),newquery)
                elif command == "inc":
                    for count in range(0,repeat):
                        if ',' in paramString:
                            params = paramString.split(',')
                            incrementVar(params[0],params[1],newquery)
                        else:
                            incrementVar(paramString,newquery)
                elif command == "dec":
                    for count in range(0,repeat):
                        if ',' in paramString:
                            params = paramString.split(',')
                            decrementVar(params[0],params[1],newquery)
                        else:
                            decrementVar(paramString,newquery)
                elif command == "expr":
                    #print ("Unpacking %s" % paramString)
                    for count in range(0,repeat):
                        (var,expr) = paramString.split('=')
                        (val1,op,val2) = filter(None,re.split(r'([+\-/*])',expr))
                        mathOp(var.strip(),op.strip(),val1.strip(),val2.strip(),newquery)
                elif command == "cancel":
                    cancelEvent(paramString)
                elif command == "print":
                    for count in range(0,repeat):
                        devices.logfile ("  > "+expandVariables(getStatus(paramString,query),query),"INFO")
                elif command.startswith('timer'):
                    minutes = "0" + command[5:]
                    seconds = float(minutes) * 60 + query['deviceDelay']
                    eventName = query['command']
                    if eventName.endswith("on"):
                        eventName = eventName[:-2]
                    elif eventName.endswith("off"):
                        eventName = eventName[:-3]
                    for count in range(0,repeat):
                        eventList.add(eventName+"-"+str(timerCount),seconds,"."+paramString,newquery)
                        timerCount = timerCount + 1
                else:
                    #devices.logfile("command = %s, param = %s" % (command,paramString), "SPECIAL")
                    if ',' in paramString and '=' in paramString:
                        for param in paramString.split(','):
                            pair = param.split('=')
                            newquery[pair[0]] = pair[1]
                    elif '=' in paramString:
                        pair = paramString.split('=')
                        newquery[pair[0]] = pair[1]
                    else:
                        if settingsFile.has_option(newquery['device'],paramString):
                            newquery['button'] = getStatus(paramString)
                        else:
                            newquery['button'] = paramString
                    for count in range(0,repeat):
                        if command == "logic":
                            execute_logicnode_raw(newquery)
                        elif command == "event":
                            execute_event_raw(newquery['device']+"-"+str(int(time.time()))[5:],newquery)
                        else:
                            if checkConditionals(command,newquery) is False:
                                sendCommand(command,newquery)
        elif "," in command:
            try:
                (actualCommand, repeatAmount) = command.split(',')
                if actualCommand == "sleep":
                    time.sleep(float(repeatAmount))
                else:
                    devices.logfile ("\t","DEBUG",end='')
                    for x in range(0,int(repeatAmount)):
                        devices.logfile (actualCommand,"DEBUG",end=' ')
                        sys.stdout.flush()
                        sendCommand(actualCommand,newquery)
            except Exception as e:
                devices.logfile ("\nSkipping malformed command: %s, %s" % (command,e),"ERROR")
        else:
            sendCommand(command,newquery)
    sys.stdout.flush()

#- Wake On Lan
def execute_wol(command,query):
    section = "WOL "+command
    #devices.logfile (section,"DEBUG")
    try:
        port = None
        mac = expandVariables(settingsFile.get(section,"mac"),query)
        ip = expandVariables(settingsFile.get(section,"ip"),query)
        if settingsFile.has_option(section,"port"):
            port = expandVariables(settingsFile.get(section,"port"),query)
        return wol.wake(mac,ip,port)
    except Exception as e:
        devices.logfile ("WOL Failed: %s" % e,"ERROR")
    return False

#- Execute shell command, short MACRO version
def shellCommand(commandString):
    #devices.logfile("SH %s" % commandString, "DEBUG")
    (command,sep,parameters) = commandString.partition(' ')
    execCommand = [command,parameters]
    try:
        retval = subprocess.check_output(execCommand,shell=False).strip()
    except subprocess.CalledProcessError as e:
        retval = "Fail: %d; %s" % (e.returncode,e.output)
    if len(retval) < 1:
        retval = 'done'
    return retval

#- Execute shell command, section version, with store ability
def execute_shell(command,query):
    section = "SHELL " + command
    #devices.logfile (section,"DEBUG")
    parameters = None
    if settingsFile.has_option(section,"parameters"):
        parameters = expandVariables(settingsFile.get(section,"parameters"),query)
    if settingsFile.has_option(section,"command"):
        command = expandVariables(settingsFile.get(section,"command"),query)
    else:
        devices.logfile ("You must specify at least a \"command\" for any SHELL command","ERROR")
    execCommand = command
    if parameters != None:
        execCommand = [command,parameters]
    shell = False
    try:
        if settingsFile.has_option(section,"shell") and settingsFile.get(section,"shell")!="False":
            retval = subprocess.check_output(execCommand)
        else:
            retval = subprocess.check_output(execCommand,shell=shell)
        if settingsFile.has_option(section,"store"):
            setStatus(expandVariables(settingsFile.get(section,"store"),query),str(retval,'utf8').strip(),query)
    except subprocess.CalledProcessError as e:
        retval = "Fail: %d; %s" % (e.returncode,e.output)
    if len(retval) < 1:
        retval = command
    return retval

#- Check if a host is up
def ping(host):
    param = '-n' if system_name().lower()=='windows' else '-c'
    command = ['ping', param, '1', host]
    return subprocess.call(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE) == 0

def execute_ping(command,query):
    section = "PING "+command
    #devices.logfile (section,"DEBUG")
    try:
        host = expandVariables(settingsFile.get(section,"host"),query)
        if ping(host):
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        # print ("Command will be %s" % rawcommand)
        result = sendCommand(rawcommand,query)
        return command
    except Exception as e:
        devices.logfile ("PING Failed: %s" % e,"ERROR")
    return False

def execute_radio(command,query):
    section = "RADIO " + command
    #devices.logfile (section,"DEBUG")
    status = getStatus(command,query)
    try:
        if settingsFile.has_option(section,'device'):
            query = query.copy()
            query['device'] = settingsFile.get(section,'device')
            if settingsFile.has_option(section,'deviceDelay'):
                query['deviceDelay'] = settingsFile.get(section,'deviceDelay')
        newstatus = query["button"]
        if (status == newstatus):
            devices.logfile ("RADIO button %s already at state = %s" % (command,status),"LOG")
            return status
        else:
            if settingsFile.has_option(section,"pre"):
                sendCommand(settingsFile.get(section,"pre"),query)

            if settingsFile.has_option(section,"sequence"):
                sequence = settingsFile.get(section,"sequence").split()
                start = sequence.index(status)
                end = sequence.index(newstatus)
#                print ("start: %s end: %s" % (start,end))
                if end > start:
                    for i in range(start,end):
                        onCommand = settingsFile.get(section,sequence[i])
                        sendCommand(onCommand,query)
                else:
                    for i in range(start,end,-1):
                        offCommand = settingsFile.get(section,sequence[i]+"off")
                        sendCommand(offCommand,query)
            else:
                if status == "off" or status == "poweroff":
                    off = "poweroff"
                else:
                    off = status + "off"
                if settingsFile.has_option(section,off):
                    offCommand = settingsFile.get(section,off)
                    if offCommand:
                        sendCommand(offCommand,query)
                on = newstatus
                if settingsFile.has_option(section,"commands"):
                    if on in settingsFile.get(section,"commands"):
                        sendCommand(on,query)
                elif settingsFile.has_option(section,on):
                    onCommand = settingsFile.get(section,on)
                    if onCommand:
                        sendCommand(onCommand,query)
                elif settingsFile.has_option(section,"else"):
                    newstatus = 'else'
                    onCommand = settingsFile.get(section,"else")
                    if onCommand:
                        sendCommand(onCommand,query)
                else:
                    newstatus = 'error'
            setStatus(command,newstatus,query)
            if settingsFile.has_option(section,"post") and newstatus != 'error':
                sendCommand(settingsFile.get(section,"post"),query)
        return command
    except Exception as e:
        devices.logfile ("RADIO %s Failed: %s" % (command,e),"ERROR")
    return status

def execute_event_raw(command,query):
    #print ("RAW: %s" % command)
    try:
        newcommand = expandVariables(query['command'],query)
        delay = 0.0
        if 'seconds' in query:
            delay += float(expandVariables(str(query['seconds']),query))
        if 'minutes' in query:
            delay += float(expandVariables(str(query['minutes']),query)) * 60
        if 'hours' in query:
            delay += float(expandVariables(str(query['hours']),query)) * 3600
        eventList.add(command,delay,newcommand,query)
        return command
    except Exception as e:
        devices.logfile ("EVENT Failed: %s" % e,"ERROR")
        traceback.print_exc()
    return False

def execute_event(command,query):
    section = "EVENT "+command
    try:
        newquery = query.copy()
        newquery['command'] = settingsFile.get(section,"command")
        for option in settingsFile.options(section):
            newquery[option] = settingsFile.get(section,option)
        execute_event_raw(command,newquery)
        return "command"
    except Exception as e:
        devices.logfile ("EVENT Failed: %s" % e,"ERROR")
    return False

def execute_logicnode_raw(query):
    try:
        value = expandVariables(query['test'],query)
        newcommand = None
        if str(value) in query:
            newcommand = expandVariables(query[str(value)],query)
        elif value.isnumeric():
            if value == "1" and "on" in query:
                newcommand  = expandVariables(query["on"],query)
                return sendCommand("." + newcommand,query)
            elif value == "0" and "off" in query:
                newcommand = expandVariables(query["off"],query)
                return sendCommand("." + newcommand,query)
            value = float(value)
            if "compare" in query:
                compareVar = expandVariables(query["compare"],query)
                try:
                    compare = float(compareVar)
                except:
                    compare = float(getStatus(compareVar,query))
            else:
                compare = 0
            newvalue = value - compare
            if newvalue < 0:
                if "less" in query:
                    newcommand = expandVariables(query["less"],query)
                elif "neg" in query:
                    newcommand = expandVariables(query["neg"],query)
            elif newvalue > 0:
                if "more" in query:
                    newcommand = expandVariables(query["more"],query)
                elif "pos" in query:
                    newcommand = expandVariables(query["pos"],query)
            else:
                if "equal" in query:
                    newcommand = expandVariables(query["equal"],query)
                elif "zero" in query:
                    newcommand = expandVariables(query["zero"],query)
        if newcommand is None:
            if "else" in query:
                newcommand = expandVariables(query["else"],query)
        if newcommand is not None:
            return sendCommand("." + newcommand,query)
        return False
    except Exception as e:
        if "error" in query:
            newcommand = expandVariables(query['error'],query)
            return sendCommand("." + newcommand,query)
        devices.logfile ("LOGIC Failed: %s" % e, "ERROR")
        traceback.print_exc()
        return False

#- LogicNode multi-branch conditional
def execute_logicnode(command,query):
    section = "LOGIC "+command
    #devices.logfile (section,"DEBUG")
    newcommand = None
    newquery = query.copy()
    newquery['command'] = command
    if settingsFile.has_option(section,"test"):
        newquery["test"] = expandVariables(settingsFile.get(section,"test"),query)
    else:
        devices.logfile ("LOGIC Failed: A test value is requiWARN","ERROR")
        return
    for var in settingsFile.options(section):
        newquery[var] = settingsFile.get(section,var)
    execute_logicnode_raw(newquery)
    return command

def checkConditionals(command,query):
    #print("checkConditions %s" % command)
    if settingsFile.has_section("LOGIC "+command):
        return execute_logicnode(command,query)
    elif settingsFile.has_section("PING "+command):
        return execute_ping(command,query)
    elif settingsFile.has_section("WOL "+command):
        return execute_wol(command,query)
    elif settingsFile.has_section("SHELL "+command):
        return execute_shell(command,query)
    elif settingsFile.has_section("EVENT "+command):
        return execute_event(command,query)
    elif settingsFile.has_section("RADIO "+command):
        return execute_radio(command,query)
    else:
        return False

def init_callbacks(settings,sendRef,getStatRef,setStatusRef,toggleStatusRef):
    global settingsFile,sendCommand,getStatus,setStatus,toggleStatus
    settingsFile = settings
    sendCommand = sendRef
    getStatus = getStatRef
    setStatus = setStatusRef
    toggleStatus = toggleStatusRef

