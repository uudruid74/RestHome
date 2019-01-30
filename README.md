RestHome - Home Automation Backend Server with REST API
=======================================================
Supported devices: Most broadlink devices, anything supported by IFTTT, others via shell script
-----------------------------------------------------------------------------------------------

PYTHON 3.x READY and 2.x is no longer supported!  Min version: 3.6!

Uses [python-broadlink](https://github.com/mjg59/python-broadlink)
Based and inspired by [BlackBeanControl](https://github.com/davorf/BlackBeanControl)
Originally forked from [broadlink-http-rest](https://github.com/radinsky/broadlink-http-rest)

Real PDF Documentation (source is in LyX) on the programming options is underway!


System Features
---------------
- **Multithreaded**     Responsive, handles multiple clients, programmable events and timers
- **Programmable**      Macro Language contains variables, loops, conditions, and shell integration
- **IFTTT Integration** Send or Recieve commands from IFTTT to control anything IFTTT can control
- **Virtual Devices**   A single broadlink can control multiple virtual devices
- **Chromecast**        Integrated Chromecast functions are COMING SOON!
- **Fast Learning**     No more waiting 20 seconds to learn every command!
- **Web Scraping**      Read information from websites into variables
- **State Safety**      Define startup/shutdown commands to restore sane state
- **Webserver**         Internal web server for media (think Chromecast and UI) in progress!
- **Security**          Understands SSL proxies with appropriate whitelist security
- **Definable UI**      The "testing" UI is just starting.  Currently view only while I standardize controls some

Theory Of Operation
-------------------
RestHome was designed to be lightweight and easy to configure.  Rather than a
complex programming language or configuration syntax, RestHome uses a simple
INI file to control its operation.  The concepts of "Scenes" has been replaced
with "Macros".  Basically, the INI file defines Devices, Commands for those
devices, and Status variables for those commands to use.  Commands are simply
sent to devices as the data given in the command definition.  If the command
definition begins with a period or the word MACRO, it should be a list of
command names.  The list is done in order.  Some built-in commands may be 
pre-defined such as sleeping (in seconds), creating timer events (in minutes, 
but fractions are allowed), and simple logic.

Programmability is through simple node-based logic, the "Radio" button sections
(see macros.txt), triggers (do something any time a variable is written), and 
various others, such as PING, WOL, etc.  These simple yet powerful constructs
can emulate a number of common programming tasks.

Actual devices are through a plugin system.  Currently, only plugins for
broadlink devices, webhook/rest based devices (including all of IFTTT), LOG
files, and virtual devices are supported.  Creating new plugins is done by
creating a new file defining a few callback functions in python and dropping
it into the plugin directory.  A simple UI is underway as well as more plugins,
including native Google Assistant, Chromecast, RRD Tool, MQTT, and possibly an
"Array" plugin.


Example usage
-------------

1) Update settings.ini with your configuration

After viewing the sample settings.ini, erase it! The system will autodetect your devices.  It *should* tell you what optional modules need to be installed for various features

The [General] section contains the following optional parameters
- **ServerAddress** = IP to listen on, rather than 0.0.0.0
- **ServerPort** = listen port (defaults to 8080)
- **Timeout** = Default timeout for network operations in seconds (default 8)
- **DiscoverTimeout** = Device discovery timeout, defaults to the same as Timeout
- **LearnFrom** = IP addresses that can issue new commands to learn from (default is any)
- **BroadcastAddress** = a pending patch to python-broadlink will allow device discover to use a specified broadcast IP
- **Autodetect** = if set to a number, do device discover for the given number of seconds.  This option removes itself.
- **AllowOverwrite** = if set to anything, allow learned commands to overwrite an existing entry.  The default is to deny a command that is already learned
- **RestrictAccess** = restrict all operations to this list of IPs
- **Password** = allow password-protected POST operations from any address
- **MaxThreads** = maximum number of processing threads, defaults to 16
- **Hostname** = remote hostname for forming URLs in local media and UI tools
- **House** = name of a device representing the entire house

If _Password_ is specified, then GET operations are only allowed from hosts in _RestrictAccess_.  GET operations won't need a password, but they'll only be allowed from specific hosts.  There is currently no way to restrict hosts AND require a password, but _serverAddress_ combined with firewall rules on the underlying host would be solution for the security paranoid, setting _Password_ and not _RestrictAccess_.


2) Start python server.py

Note the names of the devices found.  These will be named by the hostname, so make sure the IP address resolves or enter
it in /etc/hosts before you begin.  You can also manually rename the devices in settings.ini


3) In your browser:

```
http://localhost:8080/deviceName/learnCommand/mute  # learn command with name lamp
http://localhost:8080/deviceName/sendCommand/lampon # send command with name lamp, set lamp to 1
```


4) Get and Set status of devices having COMMANDon and COMMANDoff abilities
```
http://localhost:8080/deviceName/sendCommand/lampon # automatically set status of "lamp" to "on"
http://localhost:8080/deviceName/getStatus/lamp     # return lamp status as 0 or 1
```


5) Check pending events (client must be on the restrictAccess list)
```
http://localhost:8080/listEvents                    # list all pending events
```
Response:
```
{
        "ok": "eventList",
        "104": "POLL_BeagleBone_temp = thermostat",
        "3404": "fetchTempLoop = >fetchTemp fetchTempLoop"
}
```


6) List Devices (client must be on the restrictAccess list)
```
http://localhost:8080/listDevices
```
Response:
```
{
        "ok": "deviceList",
        "Fireplace": "Duraflame Heater",
        "Alice": "Vizio SmartCast TV",
        "LivingRoom-BlackBean": "LivingRoom-BlackBean",
        "AV": "Sony DH770 AV Reciever",
        "AC": "GREE Air Conditioner",
        "default": "Unknown",
        "IFTTT": "IFTTT",
        "LG": "Ultra Blueray Player",
        "BeagleBone": "On-board GPIO Pins",
        "StrayScampsDen": "Entire House"
}
```


7) List Status Variables (client must be on the restrictAccess list)
```
http://localhost:8080/BeagleBone/listStatus
```
Response:
```
{
        "ok": "BeagleBone Status",
        "temp": "70"
}
```


8) List all devices by Room (if assigned to a room), starting with Household name:
```
http://localhost:8080/listRooms
```
Response:
```
{
        "ok": "StrayScampsDen",
        "KitchenHeater": "Kitchen",
        "Fireplace": "LivingRoom",
        "BedroomHeater": "Bedroom",
        "Kitchen": "Kitchen",
        "CoffeePot": "Kitchen",
        "BathroomHeater": "Bathroom",
        "Alice": "LivingRoom",
        "LG": "LivingRoom",
        "AC": "LivingRoom",
        "BeagleBone": "LivingRoom",
        "Bedroom": "Bedroom",
        "AV": "LivingRoom"
}
```


9) Check the PDF documentation on how to program loops, conditionals, and integrate with IFTTT, etc

