import pyaudio
import json
import os

def list_audio_devices():
    """List all available audio input and output devices with consecutive numbering"""
    p = pyaudio.PyAudio()
    
    input_devices = []
    input_device_map = {}  # Maps display number to actual device index
    input_counter = 0
    
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if device_info['maxInputChannels'] > 0:
            input_devices.append(i)
            input_device_map[input_counter] = i
            input_counter += 1
    
    output_devices = []
    output_device_map = {}  # Maps display number to actual device index
    output_counter = 0
    
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if device_info['maxOutputChannels'] > 0:
            output_devices.append(i)
            output_device_map[output_counter] = i
            output_counter += 1
    
    p.terminate()
    return input_devices, output_devices, input_device_map, output_device_map

def load_audio_settings():
    """Load audio device settings from audio.settings file"""
    settings_file = "audio.settings"
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                return settings.get('input_device'), settings.get('output_device')
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading settings: {e}")
            return None, None
    return None, None

def save_audio_settings(input_device, output_device):
    """Save audio device settings to audio.settings file"""
    settings_file = "audio.settings"
    
    settings = {
        'input_device': input_device,
        'output_device': output_device
    }
    
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        print(f"Audio settings saved to {settings_file}")
    except Exception as e:
        print(f"Error saving settings: {e}")

def get_device_name(device_index):
    """Get device name by index"""
    p = pyaudio.PyAudio()
    try:
        device_info = p.get_device_info_by_index(device_index)
        return device_info['name']
    except:
        return f"Unknown Device ({device_index})"
    finally:
        p.terminate()

def select_audio_devices():
    """Allow user to select input and output audio devices with settings persistence"""
    # Try to load existing settings
    saved_input, saved_output = load_audio_settings()
    
    input_devices, output_devices, input_device_map, output_device_map = list_audio_devices()
    
    if not input_devices:
        print("No input devices found!")
        return None, None
    
    if not output_devices:
        print("No output devices found!")
        return None, None
    
    print("\n=== Device Selection ===")
    
    # STEP 1: Input Device Selection
    selected_input_device = None
    
    # Check if saved input device is still valid
    if saved_input is not None and saved_input in input_devices:
        input_name = get_device_name(saved_input)
        print(f"Found saved input device: {input_name}")
        use_saved = input("Use saved input device? (y/n): ").strip().lower()
        if use_saved == 'y':
            selected_input_device = saved_input
        else:
            selected_input_device = None
    else:
        selected_input_device = None
    
    # Select input device if not using saved
    if selected_input_device is None:
        print("\n--- Input Device Selection ---")
        print("Input Devices:")
        for i in range(len(input_devices)):
            device_name = get_device_name(input_devices[i])
            print(f"  {i}: {device_name}")
        
        while True:
            try:
                input_choice = input(f"Select input device (0-{len(input_devices)-1}): ").strip()
                input_display_index = int(input_choice)
                if 0 <= input_display_index < len(input_devices):
                    selected_input_device = input_device_map[input_display_index]
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    # STEP 2: Output Device Selection
    selected_output_device = None
    
    # Check if saved output device is still valid
    if saved_output is not None and saved_output in output_devices:
        output_name = get_device_name(saved_output)
        print(f"Found saved output device: {output_name}")
        use_saved = input("Use saved output device? (y/n): ").strip().lower()
        if use_saved == 'y':
            selected_output_device = saved_output
        else:
            selected_output_device = None
    else:
        selected_output_device = None
    
    # Select output device if not using saved
    if selected_output_device is None:
        print("\n--- Output Device Selection ---")
        print("Output Devices:")
        for i in range(len(output_devices)):
            device_name = get_device_name(output_devices[i])
            print(f"  {i}: {device_name}")
        
        while True:
            try:
                output_choice = input(f"Select output device (0-{len(output_devices)-1}): ").strip()
                output_display_index = int(output_choice)
                if 0 <= output_display_index < len(output_devices):
                    selected_output_device = output_device_map[output_display_index]
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    # Show final selected devices
    input_name = get_device_name(selected_input_device)
    output_name = get_device_name(selected_output_device)
    
    print(f"\nSelected Input: {input_name}")
    print(f"Selected Output: {output_name}")
    
    # Save settings
    save_audio_settings(selected_input_device, selected_output_device)
    
    print("Press SPACE to start audio streaming, ESC to exit.\n")
    
    return selected_input_device, selected_output_device