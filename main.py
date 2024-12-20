import websocket
from scapy.all import sendp, Ether, ARP, conf
import os
import rel
import ssl
from dotenv import load_dotenv
import time

load_dotenv()

# Network interface configuration
interface = None  # Change to match your actual network interface
APP_NAME = os.environ['APP_NAME']
CHANNEL_ID = bytes([int(os.environ['CHANNEL_ID'])])
event_id = 0

def list_interfaces():
    # This will print all available network interfaces
    print("Available network interfaces:")
    print(conf.ifaces)

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
    print(f"Sent ARP packet with extra data: {event_id}")

def on_message(ws, message):
    send_arp_with_extra_data(message)

def on_error(ws, error):
    print(error)
    time.sleep(5)
    reconnect()

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")
    time.sleep(5)
    reconnect()

def on_open(ws):
    print("Opened connection")
    ws.send_text(f'dest/{APP_NAME}')

def reconnect():
    ws = websocket.WebSocketApp(f"wss://streamlineanalytics.net:10010",
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)

    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, dispatcher=rel, reconnect=5, ping_interval=10)

if __name__ == "__main__":
    websocket.enableTrace(False)
    print(APP_NAME, CHANNEL_ID)
    reconnect()
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()