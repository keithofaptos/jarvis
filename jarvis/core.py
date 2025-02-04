import pyaudio
import wave
import os
import subprocess
import threading
import pygame
import speech_recognition as sr
import requests
import numpy as np
from datetime import datetime
# Web search using Perplexity API
import re
import keyboard
import threading
from queue import Queue
import logging
import sys
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('jarvis.log')
    ]
)

# Load environment variables from .env file
load_dotenv()

# Get user name from environment or use default
USER_NAME = os.getenv('USER_NAME', 'User')

# Global variables for voice control
IS_SPEAKING = False
IS_LISTENING = False

# Command history for better context
COMMAND_HISTORY = []
MAX_HISTORY = 10  # Keep last 10 commands for context

# Volume control
VOLUME = 0.5  # 50% default volume
MIN_VOLUME = 0.1
MAX_VOLUME = 1.0

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16  # Changed to Int16 for better compatibility
CHANNELS = 1
RATE = 16000  # Lower sample rate for speech recognition
RECORD_SECONDS = 5

def record_audio():
    global IS_LISTENING
    p = None
    stream = None
    try:
        IS_LISTENING = True
        p = pyaudio.PyAudio()
        logging.info("Recording for 5 seconds...")
        
        # List all available audio devices
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                logging.debug(f"Input Device {i}: {p.get_device_info_by_host_api_device_index(0, i).get('name')}")
        
        # Find the index of the default input device
        default_input = p.get_default_input_device_info()
        logging.info(f"Using input device: {default_input['name']}")
        
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       input_device_index=default_input['index'],
                       frames_per_buffer=CHUNK)
        
        frames = []
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            except IOError as e:
                logging.warning(f"Dropped audio frame due to {e}")
                continue
            except Exception as e:
                logging.error(f"Error reading audio frame: {e}")
                continue
        
        return frames
    
    except Exception as e:
        logging.error(f"Error recording audio: {e}")
        return None
    
    finally:
        IS_LISTENING = False
        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception as e:
                logging.error(f"Error closing audio stream: {e}")
        if p:
            try:
                p.terminate()
            except Exception as e:
                logging.error(f"Error terminating PyAudio: {e}")

def save_audio(frames, filename="temp.wav"):
    if frames is None:
        print("No audio data to save")
        return False
        
    p = None
    wf = None
    try:
        p = pyaudio.PyAudio()
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        return True
        
    except Exception as e:
        print(f"Error saving audio: {e}")
        return False
        
    finally:
        if wf:
            try:
                wf.close()
            except:
                pass
        if p:
            try:
                p.terminate()
            except:
                pass

# Global queue for commands
command_queue = Queue()

def keyboard_listener():
    def on_press(key):
        try:
            # Check for spacebar or 'end' typed
            if ((hasattr(key, 'char') and key.char == ' ') or \
               (hasattr(key, 'name') and key.name == 'space') or \
               (hasattr(key, 'name') and key.name == 'spacebar')):
                logging.info('Spacebar pressed - initiating exit sequence')
                print('\n(Spacebar pressed - exiting JARVIS...)')
                end_jarvis()
            elif hasattr(key, 'char'):
                # Store the last 3 characters typed
                keyboard_listener.buffer = (keyboard_listener.buffer + key.char)[-3:]
                logging.debug(f'Current keyboard buffer: {keyboard_listener.buffer}')
                if keyboard_listener.buffer == 'end':
                    logging.info('"end" typed - initiating exit sequence')
                    print('\n("end" typed - exiting JARVIS...)')
                    end_jarvis()
        except AttributeError as e:
            logging.debug(f'Special key pressed: {e}')
        except Exception as e:
            logging.error(f'Error in keyboard listener: {e}')
            print(f"\n(Error in keyboard listener: {e})")
    
    # Initialize character buffer for tracking typed 'end'
    keyboard_listener.buffer = ''
    keyboard.on_press(on_press)
    keyboard.wait()

def stop_speaking():
    global IS_SPEAKING
    try:
        logging.debug("Attempting to stop speech")
        result = subprocess.run(["pkill", "-f", "say"], 
                              check=False, 
                              capture_output=True, 
                              text=True)
        if result.returncode != 0 and result.returncode != 1:  # 1 means no process found
            logging.warning(f"pkill returned unexpected code {result.returncode}: {result.stderr}")
        IS_SPEAKING = False
        logging.debug("Speech stopped successfully")
    except Exception as e:
        logging.error(f"Error stopping speech: {e}", exc_info=True)
        IS_SPEAKING = False  # Ensure flag is reset even on error

def check_for_stop_command(source, recognizer):
    try:
        # Adjust recognition settings for better accuracy
        logging.debug("Configuring speech recognition settings")
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.5
        
        logging.debug("Listening for potential stop command...")
        audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
        
        try:
            command = recognizer.recognize_google(audio).lower()
            logging.info(f"Heard command: {command}")
            print(f"\n(Heard: {command})")
            
            # Expanded list of stop variants with more natural phrases
            stop_variants = [
                'stop JARVIS', 'JARVIS stop',
                'stop', 'please stop',
                'be quiet', 'quiet',
                'shut up', 'stop talking',
                'end JARVIS', 'JARVIS end'
            ]
            
            # More lenient matching - check if any word in the command matches any stop variant
            command_words = set(command.split())
            logging.debug(f"Command words: {command_words}")
            
            for variant in stop_variants:
                variant_words = set(variant.split())
                # Check if the important words are present (more flexible matching)
                if len(variant_words & command_words) >= len(variant_words):
                    logging.info(f"Stop command detected: {variant}")
                    print("\n(Stop command detected!)")
                    return True
            
            logging.debug("No stop command detected in utterance")
            return False
                    
        except sr.UnknownValueError:
            logging.debug("Speech not understood")
            return False
        except sr.RequestError as e:
            logging.error(f"Could not request speech recognition results: {e}")
            return False
            
    except sr.WaitTimeoutError:
        logging.debug("Listen timeout - this is normal")
        return False
    except Exception as e:
        logging.error(f"Error checking for stop command: {e}", exc_info=True)
        print(f"\n(Error checking for stop command: {e})")
        return False

def speak(text, voice="Ava"):
    global IS_SPEAKING
    process = None
    try:
        IS_SPEAKING = True
        logging.debug(f"Starting speak function with text: {text[:50]}...")
        logging.info(f"Speaking with voice {voice}: {text[:50]}...")
        
        # Using Ava voice for JARVIS
        process = subprocess.Popen(["say", "-v", voice, text])
        
        # Listen for any voice input while speaking
        r = sr.Recognizer()
        with sr.Microphone() as source:
            logging.info("Listening for interruptions while speaking...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True
            r.pause_threshold = 0.5
            
            while process and process.poll() is None:  # While speech is still playing
                try:
                    # Listen for voice commands with a short timeout
                    logging.debug("Attempting to listen for interruption while speaking...")
                    audio = r.listen(source, timeout=0.5, phrase_time_limit=2)
                    try:
                        command = r.recognize_google(audio).lower()
                        logging.info(f"Heard while speaking: {command}")
                        print(f"\n(Heard while speaking: {command})")
                        
                        # First check for stop words that should end JARVIS
                        stop_words = ['end', 'stop', 'exit', 'enough']
                        if any(word in command for word in stop_words):
                            print("\n(Stop command detected - ending JARVIS...)")
                            stop_speaking()
                            play_end_sound()
                            cleanup(force_exit=True)
                            subprocess.run(["pkill", "-9", "-f", "python app.py"])
                            os._exit(0)
                            
                        # If any other voice input is detected, stop speaking and process the new command
                        print("\n(Interruption detected - stopping current speech...)")
                        stop_speaking()
                        return process_command(command, exit_commands)
                            
                    except sr.UnknownValueError:
                        pass  # Normal when no clear speech is detected
                        
                except sr.WaitTimeoutError:
                    continue  # Normal timeout, keep listening
                except Exception as e:
                    logging.error(f"Error while listening during speech: {e}")
        
        if process:
            process.wait()
            
    except Exception as e:
        logging.error(f"Error in speak function: {e}")
        if process:
            try:
                process.kill()
            except:
                pass
    finally:
        IS_SPEAKING = False

def get_audio():
    print("Initializing audio capture...")
    r = sr.Recognizer()
    
    # Adjust recognition settings for better accuracy
    r.energy_threshold = 300  # Minimum audio energy to consider for recording
    r.dynamic_energy_threshold = True  # Dynamically adjust for ambient noise
    r.pause_threshold = 0.8  # Seconds of silence before considering the phrase complete
    
    with sr.Microphone() as source:
        print("\nAdjusting for ambient noise... Please wait...")
        # Longer ambient noise adjustment for better accuracy
        r.adjust_for_ambient_noise(source, duration=2)
        print("Listening...")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            print("Processing speech...")
            try:
                text = r.recognize_google(audio)
                print(f"\n(Heard: {text})")
                return text
            except sr.UnknownValueError:
                print("\n(Could not understand audio - please try again)")
                return None
            except sr.RequestError as e:
                print(f"\n(Error with speech recognition service: {e})")
                return None
        except sr.WaitTimeoutError:
            print("\n(No speech detected - please try again)")
            return None

def get_weather(location):
    try:
        # Using OpenWeatherMap API
        api_key = os.getenv('OPENWEATHER_API_KEY')
        if not api_key:  # This should never happen as we check at startup
            return "I'm sorry, I'm having trouble accessing weather data right now."
            
        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=imperial"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            temp = data['main']['temp']
            condition = data['weather'][0]['description']
            humidity = data['main']['humidity']
            return f"Current weather in {location}: {condition}, {temp}°F with {humidity}% humidity."
        else:
            return f"Couldn't find weather data for {location}."
    except Exception as e:
        return f"Error getting weather: {str(e)}"

def search_web(query, num_results=3):
    try:
        api_key = os.getenv('PERPLEXITY_API_KEY')
        if not api_key:
            return "Error: Perplexity API key not found"
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that provides concise, accurate information."},
                {"role": "user", "content": query}
            ],
            "max_tokens": 300
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Error: API returned status code {response.status_code}"
    except Exception as e:
        return f"Error searching web: {str(e)}"

def enhance_prompt_with_context(prompt):
    # Check if it's a weather query
    weather_match = re.search(r'weather\s+(?:in|at|for)?\s+([\w\s,]+)', prompt.lower())
    if weather_match:
        location = weather_match.group(1).strip()
        weather_info = get_weather(location)
        return f"Based on real-time data: {weather_info}\n\nUser query: {prompt}"
    
    # For other queries, search the web
    if any(keyword in prompt.lower() for keyword in ['current', 'latest', 'recent', 'news', 'today', 'now']):
        search_results = search_web(prompt)
        return f"Based on recent web search:\n{search_results}\n\nUser query: {prompt}"
    
    return prompt

def query_llm(prompt):
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:  # This should never happen as we check at startup
        return "I'm sorry, I'm having trouble accessing my language model right now."

    # Enhance prompt with real-time data if needed
    enhanced_prompt = enhance_prompt_with_context(prompt)
    print("\nEnhanced prompt with real-time data:", enhanced_prompt)

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost:3000",
        "X-Title": "Voice LLM Tool"
    }

    payload = {
        "model": "mistralai/mistral-small-24b-instruct-2501",
        "messages": [
            {"role": "system", "content": "You are JARVIS, a helpful and friendly AI assistant. You have access to real-time information through web searches and APIs. Keep your responses concise and natural, as if having a conversation."},
            {"role": "user", "content": enhanced_prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        llm_reply = data["choices"][0]["message"]["content"]
        print("LLM Reply:", llm_reply)
        return llm_reply
    except Exception as e:
        print(f"Exception during LLM query: {e}")
        return "An exception occurred while querying the LLM."

def listen_for_wake_word():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=1, phrase_time_limit=2)
            try:
                text = r.recognize_google(audio).lower()
                print(f"\n(Heard: {text})")
                if 'hello JARVIS' in text:
                    return True
            except sr.UnknownValueError:
                pass
        except (sr.WaitTimeoutError, Exception):
            pass
    return False

def show_command_legend():
    print("""
╔════════════════ JARVIS Command Legend ════════════════╗
║                                                      ║
║  🗣️  Voice Commands:                                 ║
║     • "Hello JARVIS"      - Wake up JARVIS          ║
║     • "JARVIS stop"       - Pause JARVIS            ║
║     • "End JARVIS"        - Close the program       ║
║     • "Stop" or "Quiet"   - Stop current speech     ║
║                                                      ║
║  ⌨️  Keyboard Commands:                              ║
║     • [SPACEBAR]          - Stop current speech     ║
║     • [Ctrl+C]            - Exit program           ║
║                                                      ║
║  💡 Tips:                                           ║
║     • Speak clearly and naturally                    ║
║     • Wait for JARVIS to finish speaking            ║
║     • Say "Hello JARVIS" to resume after pausing    ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
""")

def process_command(user_input, exit_commands):
    """Process voice commands and return appropriate action"""
    try:
        logging.debug(f"Processing command: {user_input}")
        
        # Input validation
        if not user_input:
            logging.debug("Empty input received, continuing...")
            return 'continue'
        
        if not isinstance(user_input, str):
            logging.warning(f"Unexpected input type: {type(user_input)}")
            return 'continue'
            
        # Add to command history
        global COMMAND_HISTORY
        COMMAND_HISTORY.append({
            'timestamp': datetime.now().isoformat(),
            'command': user_input,
            'processed': False
        })
        if len(COMMAND_HISTORY) > MAX_HISTORY:
            COMMAND_HISTORY.pop(0)
            
        # Process input
        user_input_lower = user_input.lower()
        user_words = set(user_input_lower.split())
        logging.debug(f"Processed words: {user_words}")
        
        # Check for volume control
        global VOLUME
        volume_words = {'louder', 'quieter', 'volume', 'softer'}
        if user_words.intersection(volume_words):
            if any(word in user_input_lower for word in ['louder', 'increase']):
                VOLUME = min(VOLUME + 0.1, MAX_VOLUME)
                msg = f"Volume increased to {int(VOLUME * 100)}%"
                logging.info(msg)
                return msg
            elif any(word in user_input_lower for word in ['quieter', 'softer', 'decrease']):
                VOLUME = max(VOLUME - 0.1, MIN_VOLUME)
                msg = f"Volume decreased to {int(VOLUME * 100)}%"
                logging.info(msg)
                return msg
            elif 'volume' in user_input_lower:
                # Try to extract a percentage
                match = re.search(r'\b(\d+)%?\b', user_input_lower)
                if match:
                    new_volume = int(match.group(1)) / 100
                    if MIN_VOLUME <= new_volume <= MAX_VOLUME:
                        VOLUME = new_volume
                        msg = f"Volume set to {int(VOLUME * 100)}%"
                        logging.info(msg)
                        return msg
                msg = f"Current volume is {int(VOLUME * 100)}%"
                logging.info(msg)
                return msg
        
        # Check for history-related commands
        if any(word in user_words for word in ['repeat', 'again']):
            if len(COMMAND_HISTORY) > 1:
                # Get the previous command
                prev_cmd = COMMAND_HISTORY[-2]['command']  # -2 because -1 is current command
                logging.info(f"Repeating previous command: {prev_cmd}")
                print(f"\n(Repeating: {prev_cmd})")
                return process_command(prev_cmd, exit_commands)
            else:
                return "I don't have any previous commands to repeat."
        
        # Check for stop words that should end JARVIS
        stop_words = ['end', 'stop', 'exit', 'enough']
        for word in stop_words:
            if word in user_input_lower:
                logging.info(f"Stop word detected: {word}")
                print("\n(Stop command detected - ending JARVIS...)")
                end_jarvis()
                return 'exit'
        
        # Check for specific commands (weather, etc.)
        if 'weather' in user_words:
            logging.debug("Weather command detected")
            # Weather handling logic would go here
            pass
        
        # Mark command as processed
        COMMAND_HISTORY[-1]['processed'] = True
        
        logging.debug("No specific command matched, treating as query")
        return 'query'
        
    except Exception as e:
        logging.error(f"Error processing command: {e}", exc_info=True)
        print(f"\n(Error processing command: {e})")
        return 'continue'

def check_api_keys():
    """Check if required API keys are set and validate them"""
    missing_keys = []
    invalid_keys = []
    
    # Check OpenRouter API key
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_key:
        missing_keys.append('OPENROUTER_API_KEY')
    else:
        # Validate OpenRouter key
        try:
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "HTTP-Referer": "https://localhost:3000",
            }
            response = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
            if response.status_code != 200:
                invalid_keys.append('OPENROUTER_API_KEY')
        except Exception as e:
            logging.error(f"Error validating OpenRouter API key: {e}")
            invalid_keys.append('OPENROUTER_API_KEY')
    
    # Check OpenWeather API key
    weather_key = os.getenv('OPENWEATHER_API_KEY')
    if not weather_key:
        missing_keys.append('OPENWEATHER_API_KEY')
    else:
        # Validate OpenWeather key
        try:
            response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={weather_key}")
            if response.status_code != 200:
                invalid_keys.append('OPENWEATHER_API_KEY')
        except Exception as e:
            logging.error(f"Error validating OpenWeather API key: {e}")
            invalid_keys.append('OPENWEATHER_API_KEY')
            
    # Check Perplexity API key
    perplexity_key = os.getenv('PERPLEXITY_API_KEY')
    if not perplexity_key:
        missing_keys.append('PERPLEXITY_API_KEY')
    else:
        # Validate Perplexity key
        try:
            headers = {
                "Authorization": f"Bearer {perplexity_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "sonar-pro",
                "messages": [
                    {"role": "user", "content": "Hi"}
                ]
            }
            response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
            if response.status_code != 200:
                invalid_keys.append('PERPLEXITY_API_KEY')
        except Exception as e:
            logging.error(f"Error validating Perplexity API key: {e}")
            invalid_keys.append('PERPLEXITY_API_KEY')
    
    if missing_keys or invalid_keys:
        if missing_keys:
            logging.error("\n⚠️  Missing required API keys:")
            for key in missing_keys:
                logging.error(f"   • {key}")
        if invalid_keys:
            logging.error("\n⚠️  Invalid API keys:")
            for key in invalid_keys:
                logging.error(f"   • {key}")
        logging.error("\nPlease set valid API keys in your .env file:")
        logging.error("OPENROUTER_API_KEY='your_key_here'")
        logging.error("OPENWEATHER_API_KEY='your_key_here'")
        logging.error("PERPLEXITY_API_KEY='your_key_here'")
        return False
    
    logging.info("✅ All API keys are valid")
    return True

def play_sound(sound_type):
    """Play a sound file at the current volume setting"""
    try:
        global VOLUME
        sound_file = os.path.join(os.path.dirname(__file__), 'sounds', f'{sound_type}.mp3')
        if not os.path.exists(sound_file):
            logging.warning(f"{sound_type} sound file not found at: {sound_file}")
            return
            
        logging.debug(f"Playing {sound_type} sound at {int(VOLUME * 100)}% volume: {sound_file}")
        
        # Initialize mixer if not already initialized
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                logging.error(f"Failed to initialize pygame mixer: {e}", exc_info=True)
                return
        
        try:
            pygame.mixer.music.set_volume(VOLUME)
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play()
            
            # Wait for the sound to finish playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
        except Exception as e:
            logging.error(f"Failed to play {sound_type} sound: {e}", exc_info=True)
            # Only quit mixer if we hit an error
            try:
                pygame.mixer.quit()
            except Exception as quit_error:
                logging.error(f"Failed to quit pygame mixer after error: {quit_error}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error in play_sound: {e}", exc_info=True)

def play_startup_sound():
    play_sound('startup')

def play_end_sound():
    play_sound('endapp')

def end_jarvis():
    """Cleanly end JARVIS with sound and cleanup"""
    try:
        logging.info("Starting JARVIS shutdown sequence")
        print("\n(Ending JARVIS...)")
        
        try:
            stop_speaking()
        except Exception as e:
            logging.error(f"Error stopping speech: {e}")
        
        try:
            speak(f"Ok {USER_NAME}, goodbye.")
        except Exception as e:
            logging.error(f"Error in goodbye message: {e}")
        
        # Note: No need to play end sound here, it will be played in cleanup
        try:
            cleanup(force_exit=True)
        except Exception as e:
            logging.error(f"Error in cleanup: {e}")
            # Emergency fallback - try to play end sound even if cleanup fails
            try:
                play_end_sound()
            except:
                pass
            
        try:
            subprocess.run(["pkill", "-9", "-f", "python app.py"], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error killing JARVIS process: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in process termination: {e}")
            
        logging.info("JARVIS shutdown complete")
        os._exit(0)
    except Exception as e:
        logging.critical(f"Critical error in end_jarvis: {e}")
        # Emergency fallback - try to play end sound even on critical error
        try:
            play_end_sound()
        except:
            pass
        os._exit(1)  # Emergency exit

def main():
    # Set up logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('jarvis_debug.log')
        ]
    )
    logging.info("Starting JARVIS...")
    
    # Check for required API keys
    if not check_api_keys():
        print("\nJARVIS cannot start without required API keys.")
        return
    
    # Start keyboard listener in a separate thread
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    # Show the command legend
    show_command_legend()
    
    # Play startup sound and initial greeting
    play_startup_sound()
    speak("Hello Keith, how can I help you?")
    
    waiting_for_wake_word = False
    
    # Define exit commands
    exit_commands = ['exit', 'quit', 'close JARVIS', 'JARVIS close', 'end JARVIS', 'JARVIS end']
    
    try:
        while True:
            # Check for exit command from keyboard
            try:
                if not command_queue.empty():
                    command = command_queue.get_nowait()
                    if command == 'exit':
                        speak(f"Ok {USER_NAME}, goodbye.")
                        return
            except Exception as e:
                logging.error(f"Error checking command queue: {e}")

            if waiting_for_wake_word:
                print("\nListening for 'hello JARVIS'...")
                if listen_for_wake_word():
                    speak(f"Hi {USER_NAME}, how can I help?")
                    waiting_for_wake_word = False
                    continue
            else:
                print("\nWaiting for your voice input...")
                user_input = get_audio()
                
                # Process the command
                action = process_command(user_input, exit_commands)
                
                if action == 'continue':
                    continue
                elif action == 'exit':
                    speak(f"Ok {USER_NAME}, goodbye.")
                    cleanup(force_exit=True)
                    os._exit(0)
                elif action == 'stop':
                    stop_speaking()
                    waiting_for_wake_word = True
                    print("\nJARVIS is paused. Say 'hello JARVIS' to resume.")
                    continue
                else:  # action == 'query'
                    print("Sending your query to the LLM...")
                    reply = query_llm(user_input)
                    result = speak(reply)
                    # If speak returns a command (from interruption), process it
                    if result:
                        action = result
                        continue
    finally:
        cleanup(force_exit=True)
        sys.exit(0)

def cleanup(force_exit=False):
    try:
        logging.info("Starting cleanup...")
        logging.debug(f"Cleanup called with force_exit={force_exit}")
        
        # Always play end sound first if force_exit is True
        if force_exit:
            try:
                logging.debug("Playing end sound before cleanup")
                play_end_sound()
                time.sleep(1)  # Give the sound a moment to play
            except Exception as e:
                logging.error(f"Error playing end sound: {e}", exc_info=True)
        
        # Stop any playing sounds
        try:
            if pygame.mixer.get_init():
                logging.debug("Stopping pygame mixer")
                pygame.mixer.stop()
                pygame.mixer.quit()
                logging.debug("Pygame mixer stopped")
        except Exception as e:
            logging.error(f"Error stopping pygame mixer: {e}", exc_info=True)
            
        # Kill any running speech processes
        try:
            logging.debug("Stopping speech processes")
            result = subprocess.run(["pkill", "-f", "say"], 
                                  check=False, 
                                  capture_output=True, 
                                  text=True)
            if result.returncode != 0 and result.returncode != 1:  # 1 means no process found
                logging.warning(f"pkill returned unexpected code {result.returncode}: {result.stderr}")
            logging.info("Speech processes stopped")
        except Exception as e:
            logging.error(f"Error stopping speech processes: {e}", exc_info=True)
        
        # Remove temporary audio file if it exists
        if os.path.exists("temp.wav"):
            try:
                logging.debug("Removing temporary audio file")
                os.remove("temp.wav")
                logging.info("Removed temporary audio file")
            except Exception as e:
                logging.error(f"Error removing temporary audio file: {e}", exc_info=True)
        
        # Remove log file if empty
        try:
            if os.path.exists("jarvis.log"):
                size = os.path.getsize("jarvis.log")
                logging.debug(f"Log file size: {size} bytes")
                if size == 0:
                    os.remove("jarvis.log")
                    logging.debug("Removed empty log file")
        except Exception as e:
            logging.error(f"Error cleaning up log file: {e}", exc_info=True)
        
        # Kill any other instances of this app
        try:
            logging.debug("Stopping other JARVIS instances")
            result = subprocess.run(["pkill", "-9", "-f", f"python.*{os.path.basename(__file__)}"], 
                                  check=False,
                                  capture_output=True,
                                  text=True)
            if result.returncode != 0 and result.returncode != 1:
                logging.warning(f"pkill returned unexpected code {result.returncode}: {result.stderr}")
            logging.info("Stopped other JARVIS instances")
        except Exception as e:
            logging.error(f"Error stopping other instances: {e}", exc_info=True)
        
        logging.info("Cleanup completed successfully")
        
        if force_exit:
            logging.info("JARVIS shutting down...")
            os._exit(0)  # Force exit the program
            
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")
        if force_exit:
            os._exit(1)  # Force exit even if cleanup failed

if __name__ == "__main__":
    try:
        # Clean up any existing instances before starting
        cleanup()
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        cleanup()
    except Exception as e:
        print(f"\nError: {e}")
        cleanup()