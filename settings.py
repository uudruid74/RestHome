import configparser
import netaddr
import devices
from os import path

applicationDir = path.dirname(path.abspath(__file__))
settingsINI = path.join(applicationDir, 'settings.ini')

settings = configparser.ConfigParser()
settings.read(settingsINI)

DiscoverTimeout = GlobalTimeout = 20
if settings.has_option('General', 'Timeout'):
    DiscoverTimeout = GlobalTimeout = int(settings.get('General', 'Timeout').strip())
if settings.has_option('General', 'DiscoverTimeout'):
    DiscoverTimeout = int(settings.get('General','DiscoverTimeout').strip())

for section in settings.sections():
    #- Special sections, not a device
    if section == 'General' or 'Commands' in section or 'Status' in section:
        continue
    #- Special sections, control nodes
    if section.startswith("LOGIC ") or section.startswith("SET ") or \
            section.startswith("TEST ") or section.startswith("CHECK ") or \
            section.startswith("TIMER ") or section.startswith("RADIO") or \
            section.startswith("WOL ") or section.startswith("SHELL "):
        continue
    #- These are devices
    print(("Configured Device: %s" % section))
    Dev = devices.Dev[section] = {}

    if settings.has_option(section,'IPAddress'):
        Dev['IPAddress'] = settings.get(section,'IPAddress').strip()
    if settings.has_option(section,'IPAddress'):
        Dev['MACAddress'] = netaddr.EUI(settings.get(section, 'MACAddress'))
    if settings.has_option(section,'URL'):
        Dev['URL'] = settings.get(section,'URL').strip()
    if settings.has_option(section,'Timeout'):
        Dev['Timeout'] = int(settings.get(section, 'Timeout').strip())
    else:
        Dev['Timeout'] = 6
    if settings.has_option(section,'Delay'):
        Dev['Delay'] = float(settings.get(section, 'Delay').strip())
    else:
        Dev['Delay'] = 0.0
    #print '''Setting "%s" delay to "%s"''' % (section,Dev[section,'Delay'])
    if settings.has_option(section,'Device'):
        Dev['Device'] = int(settings.get(section, 'Device').strip(),16)
    else:
        Dev['Device'] = None
    if settings.has_option(section,'Type'):
        Dev['Type'] = settings.get(section,'Type').strip()
    #    print ("Config: %s device has Type: %s" % (section,Dev[section,'Type']))
    else: #- For legacy settings.ini support - will be removed soon
        Dev['Type'] = section.strip()[-2:]
    if settings.has_option(section,'StartUpCommand'):
        Dev['StartUpCommand'] = settings.get(section,'StartUpCommand').strip()
    else:
        Dev['StartUpCommand'] = None
    devices.DevList.append(section.strip())

