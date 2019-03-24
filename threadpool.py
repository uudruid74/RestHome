import threading
import http.server
import macros
import devices
import datetime
threadcount = 1
ShutdownRequested = threading.Event()
InterruptRequested = threading.Event()

class ThreadId(threading.local):
    def __init__(self):
        self.val = {}

class Thread(threading.Thread):
    def __init__(self, dev, sock, addr, handler, sendcommand, getstatus, setstatus):
        global threadid
        global threadcount
        threading.Thread.__init__(self)
        self.threadid = threadcount
        threadcount = threadcount+1
        self.sock = sock
        self.addr = addr
        self.daemon = True
        self.dev = dev
        self.handler = handler
        self.sendCommand = sendcommand
        self.getStatus = getstatus
        self.setStatus = setstatus
        self.start()

    def run(self):
        httpd = http.server.HTTPServer(self.addr, self.handler, False)

        # Prevent the HTTP server from re-binding every handler.
        # https://stackoverflow.com/questions/46210672/
        httpd.socket = self.sock
        httpd.threadid = self.threadid
        httpd.timeout = 2   #- socket timeout
        httpd.server_bind = self.server_close = lambda self: None

        if 'startup' in devices.Dev[self.dev]:
            devices.Dev[self.dev]['startup'](self.setStatus,self.getStatus,self.sendCommand)

        while not InterruptRequested.is_set():
#            print ("Start thread %s" % self.threadid)
            while macros.eventList.nextEvent() < 1:
                event = macros.eventList.pop()
                devices.logfile ("  = EVENT (%s) %s/%s" % (datetime.datetime.now().strftime("%I:%M:%S"),event.params['device'],event.name),"EVENT")
                if event.name.startswith("POLL_"):
                    (POLL,devicename,argname) = event.name.split('_',2)
                    value = devices.Dev[devicename]["pollCallback"](devicename,argname,event.command,event.params)
                    if value is not False:
                        if value is not None and value != '':
                            self.setStatus(argname,str(value),event.params)
                        self.sendCommand(event.command,event.params)
                else:
                    self.sendCommand(event.command,event.params)
            httpd.handle_request()
#            print ("End thread %s" % self.threadid)


