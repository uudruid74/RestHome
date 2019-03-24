# A Wake on LAN program that allows you to send magic packets over the Internet
# Based on code by Ryan Schuetzler https://gist.github.com/rschuetzler/8854764

import socket, struct

def makeMagicPacket(macAddress):
    # Take the enteWARN MAC address and format it to be sent via socket
    splitMac = str.split(macAddress,':')

    # Pack together the sections of the MAC address as binary hex
    hexMac = struct.pack('BBBBBB', int(splitMac[0], 16),
                             int(splitMac[1], 16),
                             int(splitMac[2], 16),
                             int(splitMac[3], 16),
                             int(splitMac[4], 16),
                             int(splitMac[5], 16))

    return '\xff' * 6 + macAddress * 16
                                    #create the magic packet from MAC address

def sendPacket(packet, destIP, destPort):
    print(("sendPacket %s:%s" % (destIP,destPort)))
    # Create the socket connection and send the packet
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(packet,(destIP,destPort))
    s.close()

def wake(macAddress, destIP, destPort=9):
    print(("Waking %s at %s" % (destIP, macAddress)))
    macAddressStr = str(macAddress)
    if destPort == None:
        destPort = 9
    try:
        packet = makeMagicPacket(macAddressStr)
        sendPacket(packet, destIP, destPort)
        print('Packet successfully sent to', macAddress)
        return "Sent"
    except Exception as e:
        print(("WOL Failed: %s" % e))
        return False


