from websockets.sync.client import connect
from scapy.all import sendp, Ether, ARP
import os
from dotenv import load_dotenv
import time
import threading

load_dotenv()
websocket_server_url = "ws://5.133.9.244:10010"

# Network interface configuration
interface = None  # Change to match your actual network interface
APP_NAME = os.environ['APP_NAME']
CHANNEL_ID = bytes([int(os.environ['CHANNEL_ID'])])
event_id = 0
stop_event = threading.Event()  # Event to signal stopping the main loop

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

def send_ping(ws):
    while not stop_event.is_set():
        try:
            ws.send("ping")
            print("Sent ping message")
        except Exception as e:
            print("Ping failed:", e)
            stop_event.set()  # Signal the main thread to stop
            break
        time.sleep(30)  # Send ping every 30 seconds

if __name__ == "__main__":
    print(APP_NAME, CHANNEL_ID)

    while True:
        try:
            with connect(websocket_server_url) as ws:
                ws.send(f'dest/{APP_NAME}')
                print('Opened connection')
                
                stop_event.clear()
                # Start a background thread for pinging
                ping_thread = threading.Thread(target=send_ping, args=(ws,), daemon=True)
                ping_thread.start()
                
                while not stop_event.is_set():
                    try:
                        message = ws.recv(timeout=60)
                        on_message(message)
                        print(f"Received: {message}")
                    except Exception:
                        print("No message received")
                ws.close()
                print('Closed connection')
        except Exception as e:
            print('Connection error:', e)

        time.sleep(10)  # Wait before retrying the connection