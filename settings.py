import shutil
import configparser
import netaddr
import devices
from os import path

applicationDir = path.dirname(path.abspath(__file__))
settingsINI = path.join(applicationDir, 'settings.ini')

settings = configparser.ConfigParser()
settings.read(settingsINI)

DiscoverTimeout = GlobalTimeout = 40
devices.Dev['default'] = None
if settings.has_option('General', 'Timeout'):
    DiscoverTimeout = GlobalTimeout = int(settings.get('General', 'Timeout').strip())
if settings.has_option('General', 'DiscoverTimeout'):
    DiscoverTimeout = int(settings.get('General','DiscoverTimeout').strip())
if settings.has_option('General', 'Hostname'):
    Hostname = settings.get('General','Hostname')
else:
    Hostname = 'localhost'
if settings.has_option('General','DefaultUI'):
    DefaultUI = settings.get("General","DefaultUI")
else:
    DefaultUI = "default"
if settings.has_option('General','PostalAddress'):
    PostalAddress = settings.get_option("PostalAddress")
else:
    PostalAddress = ''
if settings.has_option('General','House'):
    devices.Dev['default'] = settings.get('General','House')
    devices.setHome(devices.Dev['default'])
if settings.has_option('General','CustomDash'):
    devices.setDash(settings.get('General','CustomDash'))

for section in settings.sections():
    #- Special sections, not a device
    if section == 'General' or 'Commands' in section or 'Status' in section:
        continue
    #- Special sections, control nodes
    if section.startswith("LOGIC ") or section.startswith("TRIGGER ") or \
            section.startswith("PING ") or \
            section.startswith("EVENT ") or section.startswith("RADIO") or \
            section.startswith("WOL ") or section.startswith("SHELL ") or \
            section.startswith("GPIO "):
        continue
    #- These are devices
    #print(("Configured Device: [%s]" % section))
    Dev = devices.Dev[section] = {}
    if devices.Dev['default'] == None:
        devices.Dev['default'] = section
    if settings.has_option(section,'IPAddress'):
        if '$status(' in settings.get(section,'IPAddress'):
            name = settings.get(section,'IPAddress')[8:-1]
            Dev['IPAddress'] = settings.get('Status',name).strip()
        else:
            Dev['IPAddress'] = settings.get(section,'IPAddress').strip()
    if settings.has_option(section,'MACAddress'):
        Dev['MACAddress'] = netaddr.EUI(settings.get(section, 'MACAddress'))
    if settings.has_option(section,'URL'):
        Dev['URL'] = settings.get(section,'URL').strip()
    if settings.has_option(section,'Timeout'):
        Dev['Timeout'] = int(settings.get(section, 'Timeout').strip())
    else:
        Dev['Timeout'] = 6
    if settings.has_option(section,'Comment'):
        Dev['Comment'] = settings.get(section,'Comment').strip()
    else:
        Dev['Comment'] = section
    if settings.has_option(section,'Delay'):
        Dev['Delay'] = float(settings.get(section, 'Delay').strip())

    #print '''Setting "%s" delay to "%s"''' % (section,Dev[section,'Delay'])
    if settings.has_option(section,'Device'):
        try:
            Dev['Device'] = int(settings.get(section, 'Device').strip(),16)
        except:
            Dev['Device'] = settings.get(section,'Device').strip()
    else:
        Dev['Device'] = None
    if settings.has_option(section,'Room'):
        devices.addRoom(section,settings.get(section,'Room').strip())
    if settings.has_option(section,'Type'):
        Dev['Type'] = settings.get(section,'Type').strip()
    #    print ("Config: %s device has Type: %s" % (section,Dev[section,'Type']))
    else: #- For legacy settings.ini support - will be removed soon
        Dev['Type'] = section.strip()[-2:]
    if settings.has_option(section,'ShutdownCommand'):
        Dev['ShutdownCommand'] = settings.get(section,'ShutdownCommand').strip()
    else:
        Dev['ShutdownCommand'] = None
    if settings.has_option(section,'StartupCommand'):
        Dev['StartupCommand'] = settings.get(section,'StartupCommand').strip()
    else:
        Dev['StartupCommand'] = None
    if settings.has_option(section,'Actual'):
        Dev['Actual'] = settings.get(section,'Actual').strip()
    else:
        Dev['Actual'] = None
    if settings.has_option(section,'Icons'):
        Dev['Icons'] = settings.get(section,'Icons').strip()
    else:
        Dev['Icons'] = "Generic"
    devices.DevList.append(section.strip())

def backupSettings():
    try:
        shutil.copy2(settingsINI,settingsINI+".bak")
    except FileNotFoundError:
        devices.logfile ("\tNo settings.ini to backup.  Hope we're creating one!","ERROR")
    except:
        devices.logfile ("Error in backup operation!  Refusing to continue!","WARN")
        sys.exit()

def restoreSettings():
    if path.isfile(settingsINI+".bak"):
        shutil.copy2(settingsINI+".bak",settingsINI)
    else:
        devices.logfile ("Can't find backup to restore!  Refusing to make this worse!","WARN")
        sys.exit()


