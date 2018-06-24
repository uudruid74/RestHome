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
#-
#- TODO - allow status vars as parameters
#-
def checkMacros(commandFromSettings,query,deviceName):
    # print ("checkMacros %s %s" % (commandFromSettings,deviceName))
    if commandFromSettings.startswith("PRINT "):
        return string.Template(commandFromSettings[6:]).substitute(query)
    elif commandFromSettings.startswith("SH "):
        return shellCommand(string.Template(commandFromSettings[3:]).substitute(query))
    elif commandFromSettings.startswith("SET "):
        return setStatus(commandFromSettings[4:],"1",deviceName)
    elif commandFromSettings.startswith("INC "):
        variable = int(getStatus(commandFromSettings[4:],deviceName))
        variable += 1
        return setStatus(commandFromSettings[4:],variable,deviceName)
    elif commandFromSettings.startswith("DEC "):
        variable = int(getStatus(commandFromSettings[4:],deviceName))
        variable -= 1
        return setStatus(commandFromSettings[4:],variable,deviceName)
    elif commandFromSettings.startswith("CLEAR "):
        return setStatus(commandFromSettings[6:],"0",deviceName)
    elif commandFromSettings.startswith("TOGGLE "):
        return toggleStatus(commandFromSettings[7:],deviceName)
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
                    for x in range(0,int(repeatAmount)):
                        if actualCommand == "sleep":
                            time.sleep(1)
                        else:
                            sendCommand(actualCommand,query,deviceName)
                except:
                    print ("Skipping malformed command: %s" % command)
                continue
            if command.startswith("sleep"):
                result = append(result,command)
                try:
                    time.sleep(int(command[5:]))
                except:
                    print ("Invalid sleep time: %s; sleeping 2s" % command[5:])
                    time.sleep(2)
            else:
                newresult = sendCommand(command,query,deviceName)
                if newresult:
                    # print ("Result: %s" % newresult)
                    result = append(result,newresult)
        if result:
            return result
    else:
        return False #- not a macro

#- Wake On Lan
def execute_wol(command,query,deviceName):
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
def execute_test(command,query,deviceName):
    section = "TEST "+command
    try:
        valueToTest = settingsFile.get(section,"value")
        value = getStatus(valueToTest,deviceName)
        # print("TEST returned %s" % value)
        if value == "1":
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        # print ("Raw: %s" % rawcommand)
        return sendCommand(rawcommand,query,deviceName)
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
def execute_shell(command,query,deviceName):
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
            setStatus(settingsFile.get(section,"store"),retval,deviceName)
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

def execute_check(command,query,deviceName):
    # print ("Execute Check")
    section = "CHECK "+command
    try:
        host = settingsFile.get(section,"host")
        if ping(host):
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        # print ("Command will be %s" % rawcommand)
        result = sendCommand(rawcommand,query,deviceName)
        return result
    except StandardError as e:
        print ("Failed: %s" % e)
    return False

#- LogicNode multi-branch conditional
def execute_logicnode(command,query,deviceName):
    # print ("LOGIC %s %s" % (command,deviceName))
    section = "LOGIC "+command
    newcommand = None
    try:
        if settingsFile.has_option(section,"test"):
            valueToTest = settingsFile.get(section,"test")
            value = getStatus(valueToTest,query,deviceName)
            # print ("test = %s = %s" % (valueToTest,value))
        else:
            return False    #- test value required
        #- Try direct result
        if settingsFile.has_option(section,str(value)):
            newcommand = settingsFile.get(section,value)
        elif value.isnumeric():
            if value == "1" and settingsFile.has_option(section,"on"):
                newcommand = settingsFile.get(section,"on")
                return sendCommand(newcommand,query,deviceName)
            elif value == "0" and settingsFile.has_option(section,"off"):
                newcommand = settingsFile.get(section, "off")
                return sendCommand(newcommand,query,deviceName)
            value = float(value)
            if settingsFile.has_option(section,"compare"):
                compareVar = settingsFile.get(section,"compare")
                compare = float(getStatus(compareVar,query,deviceName))
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
            return sendCommand(newcommand,query,deviceName)
    except StandardError as e:
        # print ("Exception: %s" % e)
        try:
            if settingsFile.has_option(section,"error"):
                newcommand = settingsFile.get(section,"error")
            return sendCommand(newcommand,query,deviceName)
        except StandardError as e:
            print ("Failed: %s" % e)
        return False

def checkConditionals(command,query,deviceName):
    # print("checkConditions %s %s" % (command,deviceName))
    if settingsFile.has_section("LOGIC "+command):
        return execute_logicnode(command,query,deviceName)
    elif settingsFile.has_section("TEST "+command):
        return execute_test(command,query,deviceName)
    elif settingsFile.has_section("CHECK "+command):
        return execute_check(command,query,deviceName)
    elif settingsFile.has_section("WOL "+command):
        return execute_wol(command,query,deviceName)
    elif settingsFile.has_section("SHELL "+command):
        return execute_shell(command,query,deviceName)
    else:
        return False

def init_callbacks(settings,sendRef,getStatRef,setStatusRef):
    global settingsFile,sendCommand,getStatus,setStatus
    settingsFile = settings
    sendCommand = sendRef
    getStatus = getStatRef
    setStatus = setStatusRef
