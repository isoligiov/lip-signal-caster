from websockets.sync.client import connect
from scapy.all import sendp, Ether, ARP
import os
from dotenv import load_dotenv
import time

load_dotenv()
websocket_server_url = "ws://5.133.9.244:10010"

# Network interface configuration
interface = None  # Change to match your actual network interface
APP_NAME = os.environ['APP_NAME']
CHANNEL_ID = bytes([int(os.environ['CHANNEL_ID'])])
event_id = 0

def send_arp_with_extra_data(custom_data):
    global event_id
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")  # Broadcast MAC address
    arp = ARP(op=1, hwsrc=ether.src, psrc="0.0.0.0", hwdst="00:00:00:00:00:00", pdst="0.0.0.0")
    event_id_buf = bytes([event_id])
    extra_data = CHANNEL_ID + event_id_buf + custom_data
    packet = ether / arp / extra_data
    event_id = (event_id + 1) % 256

    # Send packet out on specified interface
    sendp(packet, iface=interface)
    # Prevent packet loss
    sendp(packet, iface=interface)
    print(f"Sent ARP packet with extra data: {event_id}")

def on_message(message):
    send_arp_with_extra_data(message)


if __name__ == "__main__":
    print(APP_NAME, CHANNEL_ID)

    while True:
        try:
            with connect(websocket_server_url) as ws:
                ws.send(f'dest/{APP_NAME}')
                print('Opened connection')
                while True:
                    message = ws.recv()
                    on_message(message)
                    print(f"Received: {message}")
        except Exception as e:
            print('ERR', e)
        time.sleep(10)