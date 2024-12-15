from scapy.all import *
from netfilterqueue import NetfilterQueue

ENCODING = "utf-8"
QUEUE = 1

def process_packet(packet):
    scapy_packet = IP(packet.get_payload())

    if scapy_packet.haslayer(Raw) and bytes("public", encoding=ENCODING) in scapy_packet[Raw].load:
        scapy_packet[Raw].load = scapy_packet[Raw].load.replace(bytes("public", encoding=ENCODING), bytes("secret", encoding=ENCODING))
        del scapy_packet[IP].chksum
        del scapy_packet[TCP].chksum
        packet.set_payload(bytes(scapy_packet))

    packet.accept()

nfqueue = NetfilterQueue()
nfqueue.bind(QUEUE, process_packet)

try:
    nfqueue.run()
except KeyboardInterrupt:
    pass

nfqueue.unbind()