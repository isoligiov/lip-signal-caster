from websockets.sync.client import connect
import os
from dotenv import load_dotenv
import time
import threading
from pynput import keyboard
import pyaudio
from audio import select_audio_devices
import json
import numpy as np
import collections

load_dotenv()
websocket_server_url = "ws://5.133.9.244:10001"

APP_NAME = os.environ['APP_NAME']
stop_event = threading.Event()  # Event to signal stopping the main loop

# Audio streaming variables
audio_stream = None
should_detect = False
should_output = False
CHUNK = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 44100
selected_input_device = None
selected_output_device = None

# Voice detection and caching variables
voice_threshold = 0.01  # Adjust this threshold for voice detection sensitivity
audio_cache = collections.deque(maxlen=1000)  # Cache for audio data
cache_lock = threading.Lock()
is_voice_detected = False
voice_detection_buffer = collections.deque(maxlen=10)  # Buffer for voice detection

# WebSocket variables
ws = None
ws_lock = threading.Lock()

def on_message(message):
    global should_output
    json_message = json.loads(message)
    if json_message['type'] == 'mouth':
        if json_message['data'] == 'go':
            should_output = True

def detect_voice(audio_data):
    """Detect if audio data contains voice based on amplitude threshold"""
    global voice_detection_buffer
    
    # Convert audio data to numpy array
    audio_array = np.frombuffer(audio_data, dtype=np.float32)
    
    # Calculate RMS (Root Mean Square) amplitude
    rms = np.sqrt(np.mean(audio_array**2))
    
    # Add to detection buffer
    voice_detection_buffer.append(rms)
    
    # Check if recent audio levels are above threshold
    if len(voice_detection_buffer) >= 3:
        recent_rms = np.mean(list(voice_detection_buffer)[-3:])
        return recent_rms > voice_threshold
    
    return False

def clear_audio_cache():
    """Clear the audio cache"""
    global audio_cache
    with cache_lock:
        audio_cache.clear()

def get_cached_audio():
    """Get and remove audio data from cache"""
    global audio_cache
    with cache_lock:
        if audio_cache:
            return audio_cache.popleft()
        return None

def add_to_cache(audio_data):
    """Add audio data to cache"""
    global audio_cache
    with cache_lock:
        audio_cache.append(audio_data)

# WebSocket initialization
def send_speak_message(data: str):
    global ws
    with ws_lock:
        if ws is not None:
            try:
                ws.send(json.dumps({"room": APP_NAME, "type": "cmd", "command": json.dumps({"type": "speak", "data": data})}))
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
    """Continuous audio streaming thread with voice detection and caching"""
    global audio_stream, should_detect, should_output, selected_input_device, selected_output_device
    global is_voice_detected, audio_cache
    
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
        
        # Continuously read from input and handle voice detection/caching/output
        while not stop_event.is_set():
            try:
                # Always read from microphone
                data = input_stream.read(CHUNK, exception_on_overflow=False)
                
                # Step 1: Voice detection when should_detect is True
                if should_detect:
                    if not is_voice_detected:
                        voice_detected = detect_voice(data)
                        if voice_detected:
                            is_voice_detected = True
                            print("Voice detected - starting to cache audio")
                            # Clear any old cache when starting new voice detection
                            clear_audio_cache()
                        else:
                            continue
                    
                    # Cache audio data when voice is detected
                    if is_voice_detected:
                        add_to_cache(data)
                else:
                    is_voice_detected = False
                
                # Step 2: Output cached audio when should_output is True
                if should_output:
                    cached_data = get_cached_audio()
                    if cached_data:
                        output_stream.write(cached_data)
                    else:
                        # No more cached data to output
                        print("No more cached audio to output - turning off should_output")
                        should_output = False
                        clear_audio_cache()
                
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
    Controls voice detection based on space key state.
    """
    def on_press(key):
        global should_detect
        try:
            if key == keyboard.Key.space and not should_detect:
                print("Space key pressed - starting voice detection")
                # Send space down signal via WebSocket
                send_speak_message("start")
                # Enable voice detection
                should_detect = True
        except AttributeError:
            # Special keys will raise AttributeError
            pass

    def on_release(key):
        global should_detect
        try:
            if key == keyboard.Key.space and should_detect:
                print("Space key released - stopping voice detection")
                # Send space up signal via WebSocket
                send_speak_message("stop")
                # Disable voice detection
                should_detect = False
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
                
                while not stop_event.is_set():
                    try:
                        message = ws.recv(timeout=60)
                        if message:
                            on_message(message)
                            print(f"Received: {message}")
                    except TimeoutError:
                        print('timeout error')
                        continue  # Allow checking of exit_flag
                    except Exception as e:
                        print("WebSocket error:", e)
                        stop_event.set()

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