import wol
import string
import time
from platform import system as system_name
from math import ceil as ceiling
from devices import devices, DeviceByName
from termcolor import cprint
import subprocess
import json
import threading
import sys

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
#        print "creating Eventlist"
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
#        print "Inserting"
        with self.lock:
            node.nextNode = self.begin
            #- insert into beginning
            if self.begin == None or node.timestamp < node.nextNode.timestamp:
                #print "Insert at beginning"
                self.begin = node
            else:
            #- insert into middle
                #print "Insert in middle"
                while node.nextNode.nextNode != None:
                    if node.timeStamp >= node.nextNode.timestamp:
                        node.nextNode = node.nextNode.nextNode
                    else:
                        node.nextNode = node
                        node.nextNode = node.nextNode.nextNode
                        return
            #- insert at end
                #print "Insert at end"
                node.nextNode = node
                node.nextNode = None
    def pop(self):
#        print "pop"
        with self.lock:
            retvalue = self.begin
            if retvalue is not None and retvalue.nextNode is not None:
                self.begin = retvalue.nextNode
            else:
                self.begin = None
            return retvalue
    def add(self,name,fire,command,params):
#        print "add"
        with self.lock:
            found = self.find(name)
            if found:
                cprint("Deleting old event: %s" % name,"yellow")
                self.delete(found)
            params['serialize'] = True
            self.insert(EventNode(name,fire,command,params))
    def find(self,name):
#        print "find"
        with self.lock:
            node = self.begin
            while node != None:
                if node.name == name:
                    return node
                else:
                    node = node.nextNode
            return None
    def delete(self,name):
#        print "delete"
        with self.lock:
            node = self.begin
            if node.name == name:
                self.begin = self.begin.nextNode
            while node.nextNode != None:
                if node.nextNode.name == name:
                    found = node.nextNode
                    node.nextNode = node.nextNode.nextNode
                    return found
                else:
                    node = node.nextNode
            return None

eventList = EventList()

#-
#- TODO - allow $default(var), just like $status, only a param can override the value
#-
def expandVariables(commandString,query):
    statusVar = commandString.find("$status(")
    while statusVar > -1:
        endVar = commandString.find(")",statusVar)
        if endVar < 0:
            cprint ("No END Parenthesis found in $status variable","yellow")
            statusVar = -1
        varname = commandString[statusVar+8:endVar]
        varvalue = getStatus(varname,query)
        commandString = commandString.replace(commandString[statusVar:endVar+1],varvalue)
#        print ("%s = %s device = %s" % (varname,varvalue,query['device']))
#        print ("new: %s" % commandString)
        statusVar = commandString.find("$status(")
    firstPass = commandString
    secondPass = string.Template(firstPass).substitute(query)
    return secondPass

def checkMacros(commandFromSettings,query):
    #print ("checkMacros %s" % commandFromSettings)
    if commandFromSettings.startswith("PRINT "):
        cprint (expandVariables(commandFromSettings[6:],query),"white")
        return True
    elif commandFromSettings == "NOP":
        #cprint ("%s=NOP" % query['command'],"cyan",end=' ')
        return True
    elif commandFromSettings.startswith("SH "):
        shellCommand(expandVariables(commandFromSettings[3:],query))
        return True
    elif commandFromSettings.startswith("SET "):
        return setStatus(commandFromSettings[4:],"1",query)
    elif commandFromSettings.startswith("INC "):
        variable = int(getStatus(commandFromSettings[4:],query))
        variable += 1
        setStatus(commandFromSettings[4:],str(variable),query)
        return str(variable)
    elif commandFromSettings.startswith("CANCEL "):
        variable = int(getStatus(commandFromSettings[7:],query))
        eventList.delete(variable)
        return "{ '''cancelled''': '''%s''' }" % variable
    elif commandFromSettings.startswith("DEC "):
        variable = int(getStatus(commandFromSettings[4:],query))
        variable -= 1
        setStatus(commandFromSettings[4:],str(variable),query)
        return str(variable)
    elif commandFromSettings.startswith("CLEAR "):
        return setStatus(commandFromSettings[6:],"0",query)
    elif commandFromSettings.startswith("TOGGLE "):
        return toggleStatus(commandFromSettings[7:],query)
    elif commandFromSettings.startswith("RELAY "):
        device = commandFromSettings[6:]
        if device == query['device']:
            cprint ("RELAY %s attempted to relay to itself" % query['command'],"yellow")
            return False
        newquery = query.copy()
        newquery['device'] = device
        #print "Relaying %s to %s" % (query['command'],device)
        return sendCommand(query['command'],newquery)
    elif commandFromSettings.startswith("MACRO "):
        if 'serialize' in query and query['serialize']:
            exec_macro(commandFromSettings,query)
        else:
            eventList.add(query['command'],query["deviceDelay"],commandFromSettings,query)
        return query['command']
    else:
        return False #- not a macro

def exec_macro(commandFromSettings,query):
    expandedCommand = expandVariables(commandFromSettings[6:],query)

    #cprint("expandedCommand = %s" % expandedCommand, "magenta")
    commandFromSettings = expandedCommand.strip()
    for command in commandFromSettings.split():
        newquery = query.copy()
        # print ("Executing %s" % command)
        cprint (command,"cyan",end=' ')
        sys.stdout.flush()

        if command == "sleep":
            time.sleep(1)
            continue
        if "(" in command:
            paramstring= command[command.find("(")+1:command.find(")")]
            command = command[:command.find("(")]
            #cprint("command = %s, param = %s" % (command,paramstring), "magenta")
            for param in paramstring.split(','):
                pair = param.split('=')
                newquery[pair[0]] = pair[1]
                # print ("Setting %s to %s" % (pair[0], pair[1]))
        elif "," in command:
            try:
                (actualCommand, repeatAmount) = command.split(',')
                if actualCommand == "sleep":
                    time.sleep(float(repeatAmount))
                else:
                    for x in range(0,int(repeatAmount)):
                        cprint (actualCommand,"green",end=' ')
                        sys.stdout.flush()
                        sendCommand(actualCommand,query)
            except Exception as e:
                cprint ("\nSkipping malformed command: %s, %s" % (command,e),"yellow")
            continue
        if command.startswith("sleep"):
            amount = float(command[5:].strip())
            try:
                time.sleep(amount)
            except Exception as e:
                cprint ("\nInvalid sleep time: %s (%s); sleeping 2s" % (amount,e),"yellow")
                time.sleep(2)
        else:
            result = sendCommand(command,newquery)
    sys.stdout.flush()

#- Wake On Lan
def execute_wol(command,query):
    section = "WOL "+command
    cprint (section,"green")
    try:
        port = None
        mac = settingsFile.get(section,"mac")
        ip = settingsFile.get(section,"ip")
        if settingsFile.has_option(section,"port"):
            port = settingsFile.get(section,"port")
        return wol.wake(mac,ip,port)
    except Exception as e:
        cprint ("WOL Failed: %s" % e,"yellow")
    return False

#- Test a variable for true/false
def execute_test(command,query):
    section = "TEST "+command
    cprint (section,"green")
    try:
        valueToTest = settingsFile.get(section,"value")
        value = getStatus(valueToTest,query)
        #print("TEST returned %s" % value)
        if value == "1":
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        # print ("Raw: %s" % rawcommand)
        return sendCommand(rawcommand,query)
    except Exception as e:
        cprint ("TEST Failed: %s" % e,"yellow")
    return False

#- Execute shell command, short MACRO version
def shellCommand(commandString):
    cprint("SH %s" % commandString, "green")
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
    cprint (section,"green")
    parameters = None
    if settingsFile.has_option(section,"parameters"):
        parameters = expandVariables(settingsFile.get(section,"parameters"),query)
    if settingsFile.has_option(section,"command"):
        command = expandVariables(settingsFile.get(section,"command"),query)
    else:
        cprint ("You must specify at least a \"command\" for any SHELL command","yellow")
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
            setStatus(settingsFile.get(section,"store"),str(retval,'utf8').strip(),query)
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

def execute_check(command,query):
    section = "CHECK "+command
    cprint (section,"green")
    try:
        host = settingsFile.get(section,"host")
        if ping(host):
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        # print ("Command will be %s" % rawcommand)
        result = sendCommand(rawcommand,query)
        return result
    except Exception as e:
        cprint ("CHECK Failed: %s" % e,"yellow")
    return False

def execute_radio(command,query):
    section = "RADIO " + command
    cprint (section,"green")
    status = getStatus(command,query)
    try:
        newstatus = query["button"]
        if (status == newstatus):
            cprint ("RADIO button already at state = %s" % status,"cyan")
            return status
        else:
            off = "button" + status + "off"
            if settingsFile.has_option(section,off):
                offCommand = settingsFile.get(section,off)
                if offCommand:
                    sendCommand(offCommand,query)
                    time.sleep(query["deviceDelay"])
            on = "button" + newstatus + "on"
            if settingsFile.has_option(section,on):
                onCommand = settingsFile.get(section,on)
                if onCommand:
                    sendCommand(onCommand,query)
            setStatus(command,newstatus,query)
    except Exception as e:
        cprint ("RADIO Failed: %s" % e,"yellow")
    return status

def execute_timer(command,query):
    section = "TIMER "+command
    try:
        command = settingsFile.get(section,"command");
        delay = 0
        if settingsFile.has_option(section,"seconds"):
            delay += int(settingsFile.get(section,"seconds"))
        if settingsFile.has_option(section,"minutes"):
            delay += int(settingsFile.get(section,"minutes")) * 60
        if settingsFile.has_option(section,"hours"):
            delay += int(settingsFile.get(section,"hours")) * 3600
        cprint ("%s created, delay=%ss" % (section,delay),"green")
        eventList.add(command,delay,command,query)
        return command
    except Exception as e:
        cprint ("TIMER Failed: %s" % e,"yellow")
    return False

#- LogicNode multi-branch conditional
def execute_logicnode(command,query):
    section = "LOGIC "+command
    cprint (section,"green")
    newcommand = None
    try:
        if settingsFile.has_option(section,"test"):
            valueToTest = settingsFile.get(section,"test")
            value = getStatus(valueToTest,query)
            # print ("test = %s = %s" % (valueToTest,value))
        else:
            return False    #- test value required
        #- Try direct result
        if settingsFile.has_option(section,str(value)):
            newcommand = settingsFile.get(section,value)
        elif value.isnumeric():
            if value == "1" and settingsFile.has_option(section,"on"):
                newcommand = settingsFile.get(section,"on")
                return sendCommand(newcommand,query)
            elif value == "0" and settingsFile.has_option(section,"off"):
                newcommand = settingsFile.get(section, "off")
                return sendCommand(newcommand,query)
            value = float(value)
            if settingsFile.has_option(section,"compare"):
                compareVar = settingsFile.get(section,"compare")
                #print ("%s = %s" % (compareVar,getStatus(compareVar,query)))
                compare = float(getStatus(compareVar,query))
                #print ("compare = %s = %s" % (compareVar,compare))
            else:
                compare = 0
            newvalue = value - compare
            #print ("newvalue = %s" % newvalue)
            if newvalue < 0:
                if settingsFile.has_option(section,"less"):
                    newcommand = settingsFile.get(section,"less")
                elif settingsFile.has_option(section,"neg"):
                    newcommand = settingsFile.get(section,"neg")
            elif newvalue > 0:
                if settingsFile.has_option(section,"more"):
                    newcommand = settingsFile.get(section,"more")
                elif settingsFile.has_option(section,"pos"):
                    newcommand = settingsFile.get(section,"pos")
            else:
                if settingsFile.has_option(section,"equal"):
                    newcommand = settingsFile.get(section,"equal")
                elif settingsFile.has_option(section,"zero"):
                    newcommand = settingsFile.get(section,"zero")
        # print ("newcommand = %s" % newcommand)
        if newcommand == None:
            if settingsFile.has_option(section,"else"):
                newcommand = settingsFile.get(section,"else")
            else:
                return False
        else:
            return sendCommand(newcommand,query)
    except Exception as e:
        # print ("Exception: %s" % e)
        try:
            if settingsFile.has_option(section,"error"):
                newcommand = settingsFile.get(section,"error")
            return sendCommand(newcommand,query)
        except Exception as e:
            cprint ("LOGIC Failed: %s" % e,"yellow")
        return False

def checkConditionals(command,query):
    # print("checkConditions %s" % command)
    if settingsFile.has_section("LOGIC "+command):
        return execute_logicnode(command,query)
    elif settingsFile.has_section("TEST "+command):
        return execute_test(command,query)
    elif settingsFile.has_section("CHECK "+command):
        return execute_check(command,query)
    elif settingsFile.has_section("WOL "+command):
        return execute_wol(command,query)
    elif settingsFile.has_section("SHELL "+command):
        return execute_shell(command,query)
    elif settingsFile.has_section("TIMER "+command):
        return execute_timer(command,query)
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

