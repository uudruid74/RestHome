RestHome - Home Automation Backend Server with REST API
=======================================================
Supported devices: Most broadlink devices, anything supported by IFTTT, others via shell script
-----------------------------------------------------------------------------------------------

PYTHON 3.x READY and 2.x is no longer supported!

Uses [python-broadlink](https://github.com/mjg59/python-broadlink)
Based and inspired by [BlackBeanControl](https://github.com/davorf/BlackBeanControl)
Originally forked from [broadlink-http-rest](https://github.com/radinsky/broadlink-http-rest)

Real PDF Documentation (source is in LyX) on the programming options is underway!


System Features
---------------
- ** Multithreaded      **  Responsive, handles multiple clients, programmable events and timers
- ** Programmable       **  Macro Language contains variables, loops, conditions, and shell integration
- ** IFTTT Integration  **  Send or Recieve commands from IFTTT to control anything IFTTT can control
- ** Virtual Devices    **  A single broadlink can control multiple virtual devices
- ** Chromecast         **  Integrated Chromecast functions are COMING SOON!
- ** Fast Learning      **  No more waiting 20 seconds to learn every command!


Example usage
-------------

1) Update settings.ini with your configuration

After viewing the sample settings.ini, erase it! The system will autodetect your devices.  It *should* tell you what optional modules need to be installed for various features

The [General] section contains the following optional parameters
- **serverAddress** = IP to listen on, rather than 0.0.0.0
- **serverPort** = listen port (defaults to 8080)
- **Timeout** = Default timeout for network operations in tenths of a second
- **DiscoverTimeout** = Device discovery timeout, defaults to the same as Timeout
- **learnFrom** = IP addresses that can issue new commands to learn from (default is any)
- **broadcastAddress** = a pending patch to python-broadlink will allow device discover to use a specified broadcast IP
- **Autodetect** = if set to a number, do device discover for the given number of seconds.  This option removes itself.
- **allowOverwrite** = if set to anything, allow learned commands to overwrite an existing entry.  The default is to deny a command that is already learned
- **restrictAccess** = restrict all operations to this list of IPs
- **password** = allow password-protected POST operations from any address
- **MaxThreads** = maximum number of processing threads, defaults to 8

If _password_ is specified, then GET operations are only allowed from hosts in _restrictAccess_.  GET operations won't need a password, but they'll only be allowed from specific hosts.  There is currently no way to restrict hosts AND require a password, but _serverAddress_ combined with firewall rules on the underlying host would be solution for the security paranoid, setting _password_ and not _restrictAccess_.

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

5) Check pending events
```
http://localhost:8080/listEvents                    # list all pending events
```

6) Check the PDF documentation on how to program loops, conditionals, and integrate with IFTTT, etc

