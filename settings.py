import configparser
import netaddr
from os import path
from collections import defaultdict

applicationDir = path.dirname(path.abspath(__file__))
settingsINI = path.join(applicationDir, 'settings.ini')

settings = configparser.ConfigParser()
settings.read(settingsINI)

DiscoverTimeout = GlobalTimeout = 20
if settings.has_option('General', 'Timeout'):
    DiscoverTimeout = GlobalTimeout = int(settings.get('General', 'Timeout').strip())
if settings.has_option('General', 'DiscoverTimeout'):
    DiscoverTimeout = int(settings.get('General','DiscoverTimeout').strip())

DevList = []
Dev = defaultdict(dict)
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
    print ("Configured Device: %s" % section)
    if settings.has_option(section,'IPAddress'):
        Dev[section,'IPAddress'] = settings.get(section,'IPAddress').strip()
    if settings.has_option(section,'IPAddress'):
        Dev[section,'MACAddress'] = netaddr.EUI(settings.get(section, 'MACAddress'))
    if settings.has_option(section,'URL'):
        Dev[section,'URL'] = settings.get(section,'URL').strip()
    if settings.has_option(section,'Timeout'):
        Dev[section,'Timeout'] = int(settings.get(section, 'Timeout').strip())
    else:
        Dev[section,'Timeout'] = 8
    if settings.has_option(section,'Delay'):
        Dev[section,'Delay'] = float(settings.get(section, 'Delay').strip())
    else:
        Dev[section,'Delay'] = 0.0
    #print '''Setting "%s" delay to "%s"''' % (section,Dev[section,'Delay'])
    if settings.has_option(section,'Device'):
        Dev[section,'Device'] = int(settings.get(section, 'Device').strip(),16)
    else:
        Dev[section,'Device'] = None
    if settings.has_option(section,'Type'):
        Dev[section,'Type'] = settings.get(section,'Type').strip()
    #    print ("Config: %s device has Type: %s" % (section,Dev[section,'Type']))
    elif settings.has_option(section,'URL'):
        Dev[section,'Type'] = 'URL'
    else:
        Dev[section,'Type'] = section.strip()[-2:]
    if settings.has_option(section,'StartUpCommand'):
        Dev[section,'StartUpCommand'] = settings.get(section,'StartUpCommand').strip()
    else:
        Dev[section,'StartUpCommand'] = None
    DevList.append(section.strip())

