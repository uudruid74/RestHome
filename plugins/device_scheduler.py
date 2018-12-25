import devices
from termcolor import cprint
from os import path
import threading
import settings
import macros
import traceback
import time


#- The Scheduler is a sort of virtual device that can implement a variety
#- of scheduler options.  Each "device" is a schedule that can be 
#- enabled or disabled separately.  You may use setStatus/enabled/0
#- or sendCommand/enable and sendCommand/disable to change the
#- initial setting (enabled unless specified otherwise).  You may
#- specify a "weekday" parameter to restrict the schedule to a
#- particular day of the week.  Each schedule may have a "trigger"
#- that is run every "poll" (default 1 hr, on the hour) minutes or
#- you can specify times to run commands, such as "04_30" to run
#- a command at 4:30 am.   Each execution will have variables set:
#- $month, $day, $hours, $minutes, $seconds, $weekday, and $isWeekday
#- The final is a boolean

try:
    devices.Modlist['cron'] = True

except ImportError as e:
    pass


#- Any early startup code for these devices
#    def startup:

#- Any late shutdown code for these devices
#    def shutdown:

weekdays = ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
def settimeinfo(params):
    timeinfo = time.localtime()
    params['month'] = timeinfo.tm_mon
    params['day'] = timeinfo.tm_mday
    params['hours'] = timeinfo.tm_hour
    params['minutes'] = timeinfo.tm_min
    params['seconds'] = timeinfo.tm_sec
    params['weekday'] = weekdays[timeinfo.tm_wday]
    params['isWeekday'] = "True"
    if timeinfo.tm_wday > 4:
        params['isWeekday'] = "False"
    return timeinfo


def modtime(timeinfo,*,tm_mon=None,tm_mday=None,tm_hour=None,tm_min=None,tm_sec=None,tm_wday=None):
    if tm_mon == None:
        tm_mon = timeinfo.tm_mon
    if tm_mday == None:
        tm_mday = timeinfo.tm_mday
    if tm_hour == None:
        tm_hour = timeinfo.tm_hour
    if tm_min == None:
        tm_min = timeinfo.tm_min
    if tm_sec == None:
        tm_sec = 0
    if tm_wday == None:
        tm_wday = timeinfo.tm_wday
    retval = (timeinfo.tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, timeinfo.tm_yday, -1)
    return time.mktime(retval)

#- The Type attribute is used to declare what sort of device we need to return
#- otherwise is only used by the device module (this one)

def readSettings(settingsFile,devname):
    try:
        Dev = devices.Dev[devname]
        if Dev['Type'] == 'sched':
            device = type('', (), {})()
            device.varlist = []
            initialparams = {}
            if settingsFile.has_option(devname,"Device"):
                initialparams['device'] = settingsFile.get(devname,"Device")
            else:
                initialparams['device'] = devname
            (timeinfo) = settimeinfo(initialparams)
            initialparams['polltime'] = device.poll = 86400
            device.onlyWeekdays = False
            device.onlyWeekends = False
            device.enabled = True
            if settingsFile.has_option(devname,"enabled"):
                enabled = settingsFile.get(devname,"enabled")
                if enabled.lower() == "weekdays":
                    device.onlyWeekdays = True
                elif enabled.lower() == "weekends":
                    device.onlyWeekends = True
                else:
                    device.enabled = bool(enabled)
            if settingsFile.has_option(devname,"poll"):
                device.poll = float(settingsFile.get(devname,"poll")) * 60
            else:
                device.poll = 3600.0       #- 60 minutes
            if settingsFile.has_option(devname,"weekday"):
                device.weekday = settingsFile.get(devname,"weekday")
            else:
                device.weekday = '*'

            for var in settingsFile.options(devname):
                if '_' not in var:
                    continue
                (hh,mm) = var.split('_')
                nexttime = modtime((timeinfo),tm_hour=int(hh),tm_min=int(mm))
                nextevent = nexttime - time.time()
                if nextevent < 0:
                    nextevent += 86400 #- Seconds in a day
                macros.eventList.add("POLL_"+devname+"_"+var,nextevent,settingsFile.get(devname,var),initialparams)
                device.varlist.append(var)

            if settingsFile.has_option(devname,"trigger"):
                device.trigger = settingsFile.get(devname, "trigger")
                initialparams['polltime'] = device.poll
                macros.eventList.add("POLL_"+devname+"_trigger",2.0,device.trigger,initialparams)
        else:
            return False
        if 'Delay' in Dev:
            device.delay = Dev['Delay']
        else:
            device.delay = 0.0

        #- set the callbacks
        Dev['learnCommand'] = None
        Dev['sendCommand'] = sendCommand
        Dev['getStatus'] = getStatus
        Dev['setStatus'] = setStatus
        Dev['getSensor'] = None
        Dev['BaseType'] = "cron"
        Dev['pollCallback'] = pollCallback

        return device
    except Exception as e:
        cprint ("Scheduler Initialization Failed!", "red")
        traceback.print_exc()
        return None

def getStatus(device,deviceName,commandName,params):
    if commandName == 'enabled':
        if device.enabled:
            return "1"
        else:
            return "0"
        return True
    return False


def setStatus(deviceName,commandName,params,old,new):
    device = devices.DeviceByName[deviceName]
    if commandName == 'enabled':
        if new == '1':
            device.enabled = True
        else:
            device.enabled = False
        return True
    return False


#- Note that "command" is the decoded command.
#- The command name is found in params['command']
def sendCommand(command,device,deviceName,params):
    try:
        if params['command'] == 'enable':
            device.enabled = True
            return True
        elif params['command'] == 'disable':
            device.enabled = False
            return True
        return False
    except Exception as e:
        cprint("cron sendCommand: %s to %s failed: %s" % (params['command'],deviceName,e),"yellow")
        traceback.print_exc()
        return False


# Polling is an event named "POLL_devicename_argname"
def pollCallback(devicename,argname,command,params):
    device = devices.DeviceByName[devicename]
    now = time.time()
    settimeinfo(params)
    polltime = params['polltime']
    if polltime != 86400:
        nextevent = round(int(now / polltime) + 1) * polltime - now + 1
    else:
        if params['seconds'] > 0:
            nextevent = nextevent - int(params['seconds'])
    macros.eventList.add("POLL_"+devicename+"_"+argname,nextevent,command,params)

    if device.enabled and (device.weekday == params['weekday'] or device.weekday == '*'):
        if device.onlyWeekends and bool(params['isWeekday']):
            return False    #- don't run under this condition
        elif device.onlyWeekdays and not bool(params['isWeekday']):
            return False
        else:
            return None     #- perform trigger, don't set a variable
    return False    #- don't perform the trigger


devices.addReadSettings(readSettings)


