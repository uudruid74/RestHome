import wol
import string
from platform import system as system_name
import subprocess

def checkMacros(commandFromSettings, deviceName):
    print ("checkMacros %s %s" % (commandFromSettings,deviceName))
    result = ''
    if commandFromSettings.startswith("PRINT "):
        return string.Template(commandFromSettings[6:]).substitute(locals())
    elif commandFromSettings.startswith("SET "):
        return setStatus(commandFromSettings[4:],"1",deviceName)
    elif commandFromSettings.startswith("CLEAR "):
        return setStatus(commandFromSettings[6:],"0",deviceName)
    elif commandFromSettings.startswith("TOGGLE "):
        return toggleStatus(commandFromSettings[7:],deviceName)
    elif commandFromSettings.startswith("MACRO "):
        for command in commandFromSettings.strip().split():
            print ("Executing %s" % command)
            if command == "sleep":
                time.sleep(1)
                continue
            if "," in command:
                try:
                    (actualCommand, repeatAmount) = command.split(',')
                    for x in range(0,int(repeatAmount)):
                        if actualCommand == "sleep":
                            time.sleep(1)
                        else:
                            sendCommand(actualCommand,deviceName)
                except:
                    print ("Skipping malformed command: %s" % command)
                continue
            if command.startswith("sleep"):
                try:
                    time.sleep(int(command[5:]))
                except:
                    print ("Invalid sleep time: %s" % command)
                    time.sleep(2)
            else:
                result += sendCommand(command,deviceName)
                print ("Result: %s" % result)
        if result:
            return result
        return "Sent Macro %s" % command
    else:
        return False    #- not a macro

#- Wake On Lan
def execute_wol(command,deviceName):
    section = "WOL "+command
    try:
        mac = settingsFile.get(section,"mac")
        ip = settingsFile.get(section,"ip")
        if settingsFile.has_option(section,"port"):
            port = settingsFile.get(section,"port")
        return wol.wake(mac,ip,port)
    except StandardError as e:
        print ("Failed: %s" % e)
    return False

#- Test a variable for true/false
def execute_test(command,deviceName):
    section = "TEST "+command
    try:
        valueToTest = settingsFile.get(section,"value")
        value = getStatus(valueToTest,deviceName)
        print("TEST returned %s" % value)
        if value == "1":
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        print ("Raw: %s" % rawcommand)
        return sendCommand(rawcommand,deviceName)
    except StandardError as e:
        print ("Failed: %s" % e)
    return False

#- Check if a host is up
def ping(host):
    param = '-n' if system_name().lower()=='windows' else '-c'
    command = ['ping', param, '1', host]
    return subprocess.call(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE) == 0

def execute_check(command,deviceName):
    print ("Execute Check")
    section = "CHECK "+command
    try:
        host = settingsFile.get(section,"host")
        if ping(host):
            rawcommand = settingsFile.get(section,"on")
        else:
            rawcommand = settingsFile.get(section,"off")
        print ("Command will be %s" % rawcommand)
        result = sendCommand(rawcommand,deviceName)
        return result
    except StandardError as e:
        print ("Failed: %s" % e)
    return False

#- LogicNode multi-branch conditional
def execute_logicnode(command,deviceName):
    print ("LOGIC %s %s" % (command,deviceName))
    section = "LOGIC "+command
    newcommand = None
    try:
        if settingsFile.has_option(section,"test"):
            valueToTest = settingsFile.get(section,"test")
            value = getStatus(valueToTest,deviceName)
            print ("test = %s = %s" % (valueToTest,value))
        else:
            return False    #- test value required
        #- Try direct result
        if settingsFile.has_option(section,str(value)):
            newcommand = settingsFile.get(section,value)
        elif value.isnumeric():
            if value == "1" and settingsFile.has_option(section,"on"):
                newcommand = settingsFile.get(section,"on")
                return sendCommand(newcommand,deviceName)
            elif value == "0" and settingsFile.has_option(section,"off"):
                newcommand = settingsFile.get(section, "off")
                return sendCommand(newcommand,deviceName)
            value = float(value)
            if settingsFile.has_option(section,"compare"):
                compareVar = settingsFile.get(section,"compare")
                compare = float(getStatus(compareVar, deviceName))
                print ("compare = %s = %s" % (compareVar,compare))
            else:
                compare = 0
            newvalue = value - compare
            print ("newvalue = %s" % newvalue)
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
        print ("newcommand = %s" % newcommand)
        if newcommand == None:
            if settingsFile.has_option(section,"else"):
                newcommand = settingsFile.get(section,"else")
            else:
                return False
        else:
            return sendCommand(newcommand,deviceName)
    except StandardError as e:
        print ("Exception: %s" % e)
        try:
            if settingsFile.has_option(section,"error"):
                newcommand = settingsFile.get(section,"error")
            return sendCommand(newcommand,deviceName)
        except StandardError as e:
            print ("Failed: %s" % e)
        return False

def checkConditionals(command,deviceName):
    print("checkConditions %s %s" % (command,deviceName))
    if settingsFile.has_section("LOGIC "+command):
        return execute_logicnode(command,deviceName)
    elif settingsFile.has_section("TEST "+command):
        return execute_test(command,deviceName)
    elif settingsFile.has_section("CHECK "+command):
        return execute_check(command,deviceName)
    elif settingsFile.has_section("WOL "+command):
        return execute_wol(command,deviceName)
    else:
        return False

def init_callbacks(settings,sendRef,getStatRef):
    global settingsFile,sendCommand,getStatus
    settingsFile = settings
    sendCommand = sendRef
    getStatus = getStatRef

