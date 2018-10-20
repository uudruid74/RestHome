Broadlink HTTP server/proxy with REST API
==================================
Supported devices: RM/RM2/RM Pro/RM3/BlackBean/A1
-------------------------------------------------

Uses [python-broadlink](https://github.com/mjg59/python-broadlink)

Based and inspired by [BlackBeanControl](https://github.com/davorf/BlackBeanControl)

Example usage
-------------

1) Update settings.ini with your configuration

A blank file (you can erase it) is the easiest to start with, and the system will autodetect your devices.

The [General] section contains the following optional parameters
- **serverAddress** = IP to listen on, rather than 0.0.0.0
- **serverPort** = listen port (defaults to 8080)
- **Timeout** = Default timeout for network operations in tenths of a second
- **learnFrom** = IP addresses that can issue new commands to learn from (default is any)
- **broadcastAddress** = a pending patch to python-broadlink will allow device discover to use a specified broadcast IP
- **Autodetect** = if set to a number, do device discover for the given number of seconds.  This option removes itself.
- **allowOverwrite** = if set to anything, allow learned commands to overwrite an existing entry.  The default is to deny a command that is already learned
- **restrictAccess** = restrict all operations to this list of IPs
- **password** = allow password-protected POST operations from any address

If _password_ is specified, then GET operations are only allowed from hosts in _restrictAccess_.  GET operations won't need a password, but they'll only be allowed from specific hosts.  There is currently no way to restrict hosts AND require a password, but _serverAddress_ combined with firewall rules on the underlying host would be solution for the security paranoid, setting _password_ and not _restrictAccess_.

2) Start python server.py

If no devices are in settings.ini, note the names of the devices found.  These
will be named by the hostname, so make sure the IP address resolves or enter
it in /etc/hosts

3) In your browser:
```
http://localhost:8080/learnCommand/lampon   #learn command with name lampon
http://localhost:8080/sendCommand/lampon    #send command with name lampon
```
If you have more than one device, use the alternate syntax
```
http://localhost:8080/deviceName/learnCommand/lampon   #learn command with name lampon
http://localhost:8080/deviceName/sendCommand/lampon    #send command with name lampon
```

4) Added get temperature from supported devices (like RM2/Pro):
```
http://localhost:8080/getStatus/temperature
```
Returns:
```
{ "temperature": 22.2 } 
```
*required JSON format suites [homebridge-http-temperature](https://github.com/metbosch/homebridge-http-temperature) plugin.

5) Added support for A1 sensors (temperature, lights and etc..)
```
http://localhost:8080/a1/temperature
http://localhost:8080/a1/lights
http://localhost:8080/a1/noise
and etc..
```
Returns:
```
{ "temperature": 22.2 } 
{ "lights": dark } 
{ "noise": low } 
and etc..
```
*required JSON format suites [homebridge-http-temperature](https://github.com/metbosch/homebridge-http-temperature) plugin.

6) Get and Set status of devices having COMMANDon and COMMANDoff abilities
```
http://localhost:8080/sendCommand/lampon #automaticly set status of "lamp" to "on"
http://localhost:8080/getStatus/lamp     #return lamp status as 0 or 1
```

7) Added simple Macro language
Any Command can start with the word MACRO followed by a list of other commands.
Each command will be done in order.  You may repeat a command (useful for 
navigating menus) by putting a comma followed a repeat count after the command.
For example, "right,5" will send the "right" command 5 time. You can use also 
use "sleep1", "sleep2", "sleep3", etc. to insert a pause.  In this case,
a comma is optional.

Note: It may be helpful to reload your changes with SIGUSR1 when developing
macros.

8) Events and Timers
Rather than a complicated amount of code to include a full scheduler into the
system, you should schedule routine tasks with cron or other automation tool
such as IFTTT.  These tools can run something like wget or curl to run any
command, including virtual commands that can test variables.  Additionally,
two additional tools have been added.

The 'StartUpCommand' can be added to any device section and when the system
starts up, that command will be run.  Again, virtual commands are allowed.
There isn't yet an 'ExitCommand', but it could be easily added.

A 'TIMER' section has been added to allow a virtual command to trigger another
after some delay.  This is very similar to a long sleep, except that the server
won't be kept busy and can still react to other commands.  Use this to turn
on a device and automatically turn it back off after some delay.  It should
compliment your cron or other scheduler nicely.  You can run TIMER commands
from the StartUpCommand if StartUpCommand is a MACRO.


