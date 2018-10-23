import wol
import string
import time
from platform import system as system_name
import subprocess

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
    def nextEvent(self):
        if self.begin != None:
            return self.begin.timestamp - time.time()
        else:
            return 86400 #- 1 day
    def insert(self,node):
        #- insert into empty list
        if self.begin == None:
            self.begin = node
            return
        node.nextNode = self.begin
        #- insert into beginning
        if self.begin == None or node.timestamp < node.nextEvent:
            self.begin = node
        else:
        #- insert into middle
            while node.nextNode.nextNode != None:
                if node.timeStamp >= node.nextNode.timestamp:
                    node.nextNode = node.nextNode.nextNode
                else:
                    node.nextNode = node
                    node.nextNode = node.nextNode.nextNode
                    return
        #- insert at end
            node.nextNode = node
            node.nextNode = None
    def pop(self):
        retvalue = self.begin
        if retvalue != None:
            self.begin = retvalue.nextNode
        return retvalue
    def add(self,name,fire,command,params):
        found = self.find(name)
        if found:
            found.params = dict(found.params, **params)
            if found.command != command:
                print "WARNING: Event %s overwrites old command: %s" % (name,found.command)
                found.command = command
        else:
            found = EventNode(name,fire,command,params)
            self.insert(found)
    def find(self,name):
        node = self.begin
        while node != None:
            if node.name == name:
                return node
            else:
                node = node.nextNode
        return None

eventList = EventList()

#-
#- TODO - allow status vars as parameters
#-
def checkMacros(commandFromSettings,query):
    print ("checkMacros %s" % commandFromSettings)
    if commandFromSettings.startswith("PRINT "):
        return string.Template(commandFromSettings[6:]).substitute(query)
    elif commandFromSettings.startswith("SH "):
        return shellCommand(string.Template(commandFromSettings[3:]).substitute(query))
    elif commandFromSettings.startswith("SET "):
        return setStatus(commandFromSettings[4:],"1",query)
    elif commandFromSettings.startswith("INC "):
        variable = int(getStatus(commandFromSettings[4:],query))
        variable += 1
        return setStatus(commandFromSettings[4:],variable)
    elif commandFromSettings.startswith("DEC "):
        variable = int(getStatus(commandFromSettings[4:],query))
        variable -= 1
        return setStatus(commandFromSettings[4:],variable)
    elif commandFromSettings.startswith("CLEAR "):
        return setStatus(commandFromSettings[6:],"0",query)
    elif commandFromSettings.startswith("TOGGLE "):
        return toggleStatus(commandFromSettings[7:],query)
    elif commandFromSettings.startswith("MACRO "):
        expandedCommand = string.Template(commandFromSettings[6:]).substitute(query)
        commandFromSettings = expandedCommand.strip()
        result = ''
        for command in commandFromSettings.split():
            # print ("Executing %s" % command)
            if command == "sleep":
                time.sleep(1)
                result = append(result,command)
                continue
            if "," in command:
                result = append(result,command)
                try:
                    (actualCommand, repeatAmount) = command.split(',')
                    if actualCommand == "sleep":
                        time.sleep(float(repeatAmount))
                    else:
                        for x in range(0,int(repeatAmount)):
                            sendCommand(actualCommand,query)
                except StandardError as e:
                    print ("Skipping malformed command: %s, %s" % (command,e))
                continue
            if command.startswith("sleep"):
                result = append(result,command)
                try:
                    time.sleep(int(command[5:]))
                except:
                    print ("Invalid sleep time: %s; sleeping 2s" % command[5:])
                    time.sleep(2)
            else:
                newresult = sendCommand(command,query)
                if newresult:
                    # print ("Result: %s" % newresult)
                    result = append(result,newresult)
        time.sleep(0.2)
        if result:
            return result
    else:
        return False #- not a macro

#- Wake On Lan
def execute_wol(command,query):
    section = "WOL "+command
    try:
        port = None
        mac = settingsFile.get(section,"mac")
        ip = settingsFile.get(section,"ip")
        if settingsFile.has_option(section,"port"):
            port = settingsFile.get(section,"port")
        return wol.wake(mac,ip,port)
    except StandardError as e:
        print ("Failed: %s" % e)
    return False

#- Test a variable for true/false
def execute_test(command,query):
    section = "TEST "+command
    try:
        valueToTest = settingsFile.get(section,"value")
        value = getStatus(valueToTest,query)
        print("TEST returned %s" % value)
        if value == "1":
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        # print ("Raw: %s" % rawcommand)
        return sendCommand(rawcommand,query)
    except StandardError as e:
        print ("Failed: %s" % e)
    return False

#- Execute shell command, short MACRO version
def shellCommand(commandString):
    (command,sep,parameters) = commandString.partition(' ')
    execCommand = [command,parameters]
    try:
        retval = subprocess.check_output(execCommand,shell=False).strip()
    except CalledProcessError as e:
        retval = "Fail: %d; %s" % (e.returncode,e.output)
    if len(retval) < 1:
        retval = 'done'
    return retval

#- Execute shell command, section version, with store ability
def execute_shell(command,query):
    # print ("Run Subshell")

    section = "SHELL " + command
    parameters = None
    if settingsFile.has_option(section,"parameters"):
        parameters = string.Template(settingsFile.get(section,"parameters")).substitute(query)
    if settingsFile.has_option(section,"command"):
        command = string.Template(settingsFile.get(section,"command")).substitute(query)
    else:
        print ("You must specify at least a \"command\" for any SHELL command")
    execCommand = command
    if parameters != None:
        execCommand = [command,parameters]
    shell = False
    try:
        if settingsFile.has_option(section,"shell") and settingsFile.get(section,"shell")!="False":
            retval = subprocess.check_output(execCommand).strip()
        else:
            retval = subprocess.check_output(execCommand,shell=shell).strip()
        if settingsFile.has_option(section,"store"):
            setStatus(settingsFile.get(section,"store"),retval)
    except CalledProcessError as e:
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
    print ("Execute Check")
    section = "CHECK "+command
    try:
        host = settingsFile.get(section,"host")
        if ping(host):
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        # print ("Command will be %s" % rawcommand)
        result = sendCommand(rawcommand,query)
        return result
    except StandardError as e:
        print ("Failed: %s" % e)
    return False

def execute_timer(command,query):
    section = "TIMER "+command
    print ("Execute TIMER: " + command)
    try:
        command = settingsFile.get(section,"command");
        delay = 0
        if settingsFile.has_option(section,"seconds"):
            delay += int(settingsFile.get(section,"seconds"))
        if settingsFile.has_option(section,"minutes"):
            delay += int(settingsFile.get(section,"minutes")) * 60
        if settingsFile.has_option(section,"hours"):
            delay += int(settingsFile.get(section,"hours")) * 3600
        eventList.add(command,delay,command,query)
        return command
    except StandardError as e:
        print ("Failed: %s" % e)
    return False

#- LogicNode multi-branch conditional
def execute_logicnode(command,query):
    print ("LOGIC %s" % command)
    section = "LOGIC "+command
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
                compare = float(getStatus(compareVar,query))
                # print ("compare = %s = %s" % (compareVar,compare))
            else:
                compare = 0
            newvalue = value - compare
            # print ("newvalue = %s" % newvalue)
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
    except StandardError as e:
        # print ("Exception: %s" % e)
        try:
            if settingsFile.has_option(section,"error"):
                newcommand = settingsFile.get(section,"error")
            return sendCommand(newcommand,query)
        except StandardError as e:
            print ("Failed: %s" % e)
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
    else:
        return False

def init_callbacks(settings,sendRef,getStatRef,setStatusRef):
    global settingsFile,sendCommand,getStatus,setStatus
    settingsFile = settings
    sendCommand = sendRef
    getStatus = getStatRef
    setStatus = setStatusRef

