from websockets.sync.client import connect
import os
from dotenv import load_dotenv
import time
import threading
from pynput import keyboard
import pyaudio
from audio import select_audio_devices
import json

load_dotenv()
websocket_server_url = "ws://5.133.9.244:10001"

APP_NAME = os.environ['APP_NAME']
stop_event = threading.Event()  # Event to signal stopping the main loop

# Audio streaming variables
audio_stream = None
is_streaming = False
should_output = False
CHUNK = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 44100
selected_input_device = None
selected_output_device = None

# WebSocket variables
ws = None
ws_lock = threading.Lock()

# WebSocket initialization
def send_websocket_message(data: bool):
    global ws
    with ws_lock:
        if ws is not None:
            try:
                ws.send(json.dumps({"room": APP_NAME, "type": "cmd", "command": data}))
            except Exception as e:
                print(f"Failed to send data via WebSocket: {e}")
                stop_event.set()
        else:
            print("WebSocket not connected, skipping message")

def send_ping(ws_connection):
    while not stop_event.is_set():
        try:
            ws_connection.send("ping")
            print("Sent ping message")
        except Exception as e:
            print("Ping failed:", e)
            stop_event.set()  # Signal the main thread to stop
            break
        time.sleep(30)  # Send ping every 30 seconds

def audio_streaming_thread():
    """Continuous audio streaming thread that always listens to input and conditionally outputs"""
    global audio_stream, is_streaming, should_output, selected_input_device, selected_output_device
    
    try:
        p = pyaudio.PyAudio()
        
        # Open input stream (microphone) - always active
        input_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=selected_input_device,
            frames_per_buffer=CHUNK
        )
        
        # Open output stream (speakers) - always active but only used when needed
        output_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            output_device_index=selected_output_device,
            frames_per_buffer=CHUNK
        )
        
        print("Audio streaming thread started - always listening to microphone")
        is_streaming = True
        
        # Continuously read from input and conditionally write to output
        while is_streaming and not stop_event.is_set():
            try:
                # Always read from microphone
                data = input_stream.read(CHUNK, exception_on_overflow=False)
                
                # Only write to speakers when space key is pressed
                if should_output:
                    output_stream.write(data)
                    
            except Exception as e:
                print(f"Audio streaming error: {e}")
                break
        
        # Clean up streams
        input_stream.stop_stream()
        input_stream.close()
        output_stream.stop_stream()
        output_stream.close()
        p.terminate()
        print("Audio streaming thread stopped")
        
    except Exception as e:
        print(f"Failed to start audio stream: {e}")

def signal_detect_thread():
    """
    Thread responsible for detecting space key down and key up events.
    Controls audio output redirection based on space key state.
    """
    def on_press(key):
        global should_output
        try:
            if key == keyboard.Key.space and not should_output:
                print("Space key pressed - redirecting audio to output")
                # Send space down signal via WebSocket
                send_websocket_message("down")
                # Enable audio output
                should_output = True
        except AttributeError:
            # Special keys will raise AttributeError
            pass

    def on_release(key):
        global should_output
        try:
            if key == keyboard.Key.space and should_output:
                print("Space key released - stopping audio output")
                # Send space up signal via WebSocket
                send_websocket_message("up")
                # Disable audio output
                should_output = False
        except AttributeError:
            # Special keys will raise AttributeError
            pass
        
        # Stop listener on escape key (for debugging)
        if key == keyboard.Key.esc:
            return False

    # Start listening for keyboard events
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    print(APP_NAME)
    
    # Device selection
    selected_input_device, selected_output_device = select_audio_devices()
    if not selected_input_device or not selected_output_device:
        print("Failed to select audio devices. Exiting.")
        exit(1)

    # Start audio streaming thread first (always listening)
    audio_thread = threading.Thread(target=audio_streaming_thread, daemon=True)
    audio_thread.start()
    
    # Start signal detection thread
    signal_detect_thread = threading.Thread(target=signal_detect_thread, daemon=True)
    signal_detect_thread.start()

    while True:
        try:
            with connect(websocket_server_url) as ws_connection:
                print('Opened connection')
                
                # Set global ws variable
                with ws_lock:
                    ws = ws_connection
                
                stop_event.clear()
                # Start a background thread for pinging
                ping_thread = threading.Thread(target=send_ping, args=(ws_connection,), daemon=True)
                ping_thread.start()
                
                stop_event.wait()

                # Clear global ws variable
                with ws_lock:
                    ws = None
                
                ws_connection.close()
                print('Closed connection')
        except Exception as e:
            print('Connection error:', e)
            # Clear global ws variable on error
            with ws_lock:
                ws = None

        time.sleep(10)  # Wait before retrying the connection