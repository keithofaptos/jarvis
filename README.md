# JARVIS AI Assistant

A voice-controlled AI assistant inspired by Iron Man's JARVIS.

## Features

- Voice interaction with wake word detection ("Hello JARVIS")
- Natural language processing using LLM APIs
- Command history for context awareness
- Volume control through voice commands
- Interrupt-capable speech output
- Customizable startup and shutdown sounds

## Installation

### 1. System Dependencies

#### macOS
```bash
brew install portaudio python-tk
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-tk portaudio19-dev
```

#### Windows
- Install [Python](https://www.python.org/downloads/) (3.8 or higher)
- Install [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### 2. Install JARVIS

```bash
pip install jarvis-assistant
```

### 3. Configuration

#### User Name
JARVIS will address you by name. Set your name in the `.env` file:
```env
USER_NAME=Your_Name  # Default is 'User' if not set
```

#### API Keys
JARVIS requires the following API keys:

1. OpenRouter API Key (for LLM access)
   - Sign up at [OpenRouter](https://openrouter.ai)
   - Create an API key

2. OpenWeather API Key (for weather queries)
   - Sign up at [OpenWeatherMap](https://openweathermap.org)
   - Create an API key

3. Perplexity API Key (for web searches)
   - Sign up at [Perplexity](https://perplexity.ai)
   - Create an API key

Copy the template `.env` file and add your keys:
```bash
cp .env.template .env
# Edit .env and add your API keys
```

⚠️ **IMPORTANT: Never commit your `.env` file or share your API keys!** ⚠️

## Quick Start

1. Set up your environment variables in a `.env` file:
```
OPENROUTER_API_KEY=your_key_here
OPENWEATHER_API_KEY=your_key_here
PERPLEXITY_API_KEY=your_key_here
```

2. Run JARVIS:
```bash
jarvis
```

## Voice Commands

- "Hello JARVIS" - Wake up JARVIS
- "Make it louder/quieter" - Adjust volume
- "Set volume to 75%" - Set specific volume
- "Stop/End" - Exit JARVIS
- Any other phrase - Send as query to LLM

## Requirements

- Python 3.8 or higher
- System requirements:
  - PortAudio (for PyAudio)
  - SDL (for Pygame)

## Development

To set up for development:

```bash
git clone https://github.com/keithofaptos/jarvis.git
cd jarvis
pip install -e .
```

## Troubleshooting

### No Sound
- Check if your system volume is on and at a reasonable level
- Try saying "make it louder" or "set volume to 75%"
- Verify the sound files are present in the installation directory

### Microphone Issues
- Check if your microphone is properly connected and selected as the default input device
- Try running `python -m speech_recognition` to test your microphone
- On macOS, ensure microphone permissions are granted in System Preferences

### API Key Issues
- Verify all API keys are correctly set in your `.env` file
- Check if the API keys are valid by testing them directly with the respective services
- Ensure the `.env` file is in your working directory

### Installation Issues
- For PyAudio errors:
  - macOS: `brew install portaudio`
  - Ubuntu: `sudo apt-get install python3-pyaudio`
  - Windows: Use the wheel from [Unofficial Windows Binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)

### Other Issues
- Check the logs in `jarvis.log` for detailed error messages
- Try running with more verbose logging: `JARVIS_DEBUG=1 jarvis`
- Make sure all dependencies are up to date: `pip install -U jarvis-assistant`

## Support

If you encounter any issues or have questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Search for similar issues in the [GitHub Issues](https://github.com/keithofaptos/jarvis/issues)
3. Create a new issue if your problem isn't already reported

## License

MIT License - See LICENSE file for details
