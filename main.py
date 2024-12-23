import websocket
from scapy.all import sendp, Ether, ARP
import os
import rel
import ssl
from dotenv import load_dotenv
import time
import threading

load_dotenv()
websocket_server_url = "wss://streamlineanalytics.net:10010"

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
    print(f"Sent ARP packet with extra data: {event_id}")

def on_message(ws, message):
    send_arp_with_extra_data(message)

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def on_open(ws):
    print("Opened connection")
    ws.send_text(f'dest/{APP_NAME}')

def ws_thread():
    while True:
        ws = websocket.WebSocketApp(websocket_server_url,
                                on_error=on_error,
                                on_close=on_close,
                                on_open=on_open)

        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, reconnect=5, ping_interval=10, ping_timeout=9)
        time.sleep(3600 * 1)
        ws.close()

if __name__ == "__main__":
    websocket.enableTrace(False)
    print(APP_NAME, CHANNEL_ID)

    ws_thread_handler = threading.Thread(target=ws_thread)
    ws_thread_handler.start()

    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()