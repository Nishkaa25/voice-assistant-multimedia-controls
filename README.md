# Voice Assistant for MultiMedia Controls

## 5 B – Team 15 | Software Engineering

A Python-based, software-only voice assistant that enables hands-free multimedia control through spoken commands. The application uses offline speech recognition to identify user commands, processes them through a command-handling system, and controls media playback through the computer's media controls or VLC.

The assistant uses a wake word to activate command processing and provides audio feedback for successful and unrecognized commands. Speech recognition and command processing are performed locally, without depending on cloud-based speech recognition services.

## Team Members

| Name | SRN |
|---|---|
| C K Gagan Gowda | PES2UG24CS124 |
| Anudeepak Anpuraja | PES2UG24CS905 |
| Nishkaa V | PES2UG24CS907 |
| Ishanika Vinuthan | PES2UG24CS911 |

## Features

- **Wake-word activation:** Listens for the wake word `ASSISTANT` before processing multimedia commands.
- **Offline speech recognition:** Uses the Vosk speech recognition engine to convert spoken input into text locally.
- **Playback control:** Supports playing, pausing, stopping and resuming media playback.
- **Volume control:** Allows users to increase and decrease the playback volume.
- **Mute and unmute:** Supports muting and restoring audio, including retaining the previous volume level.
- **Track navigation:** Supports moving to the next or previous track in the playlist.
- **Playlist management:** Supports playlist navigation and looping through the VLC media backend.
- **Flexible media control:** Supports VLC-based control through its local HTTP interface and operating-system media controls.
- **Command recognition:** Maps different spoken phrases to predefined commands using an intent-based command parser.
- **Audio feedback:** Provides success and error chimes to indicate whether a command was executed or could not be recognized.
- **Error handling:** Handles unrecognized commands, invalid media actions, audio stream interruptions and startup failures.
- **Microphone recovery:** Includes handling for audio stream interruptions and attempts to restore microphone capture.
- **Local processing:** Speech recognition and command interpretation run locally, supporting offline operation and user privacy.

## Implementation and System Workflow

The application is organized into separate modules, with each module handling a specific part of the voice assistant's operation.

### 1. Audio Capture

The application continuously captures audio through the computer's microphone using the `sounddevice` library.

- Captures microphone input as audio data.
- Processes audio in small chunks rather than waiting for an entire recording.
- Uses a sampling rate of 16 kHz and mono audio input for speech recognition.
- Passes captured audio chunks to the speech recognition module through an audio queue.
- Handles stream interruptions and attempts microphone stream recovery when necessary.

### 2. Speech Recognition

The captured audio is processed using the Vosk speech recognition engine.

- Loads a locally stored Vosk speech recognition model.
- Converts incoming audio chunks into text.
- Processes completed recognition results to avoid executing duplicate commands from partial transcripts.
- Does not require an external speech recognition API or continuous internet access.

### 3. Wake-Word Detection

Before executing a multimedia command, the voice engine checks for the wake word `ASSISTANT`.

For example:

`ASSISTANT, play`

Once the wake word is detected, the remaining spoken phrase is extracted and passed to the command parser. The assistant can also handle a command spoken immediately after the wake word.

### 4. Command Parsing and Intent Recognition

The command parser converts recognized speech into predefined command identifiers called intents.

It normalizes the recognized text by handling differences in capitalization, punctuation and extra spaces before matching it against supported phrases.

Examples:

| Spoken Command | Recognized Intent |
|---|---|
| Play / Start | PLAY |
| Pause / Stop | PAUSE |
| Resume / Continue | RESUME |
| Volume up / Louder | VOLUME_UP |
| Volume down / Quieter | VOLUME_DOWN |
| Mute | MUTE |
| Unmute | UNMUTE |
| Next / Skip | NEXT |
| Previous / Back | PREVIOUS |

Unsupported or ambiguous phrases are rejected instead of being treated as valid multimedia commands.

### 5. Multimedia Control

The media controller receives the identified intent and executes the corresponding multimedia action.

Two control approaches are supported:

**VLC Media Player Integration**

- Communicates with VLC through its local HTTP interface.
- Uses the VLC web interface to send playback and volume-control requests.
- Supports playback controls, track navigation, volume adjustment and mute operations.
- Handles playlist navigation and looping.
- Uses configurable connection details and authentication through environment variables.

**Operating-System Media Controls**

- Uses system media keys to interact with compatible media players.
- Supports playback, volume, mute and track navigation.
- Provides an alternative backend to VLC.

The active media backend can be configured through environment variables, allowing the assistant to use the appropriate control mechanism.

### 6. Feedback and Error Handling

The feedback handler provides audio feedback after command execution.

- A success chime indicates that a command has been executed.
- An error chime indicates an unrecognized or unsupported command.
- Invalid actions are handled without allowing them to disrupt the application.
- Startup errors and microphone failures are handled with appropriate error messages.
- The application supports graceful shutdown and releases the microphone stream when exiting.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application development |
| Vosk | Offline speech recognition |
| SoundDevice | Microphone audio capture |
| NumPy | Audio-related processing support |
| VLC Media Player | Multimedia playback and HTTP-based control |
| Requests | HTTP communication with the VLC interface |
| pynput | Operating-system media key control |
| python-dotenv | Environment-based configuration |
| Pytest | Automated testing |

## System Architecture

The application follows a modular architecture in which audio input, speech recognition, command interpretation, multimedia execution and feedback are handled independently.

```text
          User Voice Input
                 |
                 v
          Audio Capture
                 |
                 v
         Offline Vosk Engine
                 |
                 v
          Wake-Word Detection
                 |
                 v
          Command Parser
                 |
                 v
           Intent Mapping
                 |
                 v
          Media Controller
                 |
          +------+------+
          |             |
          v             v
      VLC Backend    OS Media Keys
          |             |
          +------+------+
                 |
                 v
          Command Feedback
```

## Project Structure

```text
voice-assistant-multimedia-controls/
│
├── src/
│   ├── audio_capture.py
│   ├── voice_engine.py
│   ├── command_parser.py
│   ├── media_controller.py
│   └── feedback_handler.py
│
├── model/                  # Offline Vosk speech model
├── config/                 # Configuration files
├── tests/                  # Automated test cases
├── benchmarks/             # Benchmarking resources
├── synthetic_test_audio/   # Test audio samples
├── synthetic_voice_samples/# Voice sample resources
├── reports/                # Project reports and deliverables
│
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── env.example             # Example environment configuration
└── README.md
```

## Setup and Execution

### 1. Clone the Repository

```bash
git clone https://github.com/Nishkaa25/voice-assistant-multimedia-controls.git
cd voice-assistant-multimedia-controls
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure the Speech Recognition Model

Download and extract a compatible offline Vosk model into the `model/` directory.

### 5. Configure the Media Backend

Copy the example environment file:

```powershell
Copy-Item env.example .env
```

Configure the required media backend in `.env`.

For VLC:

```env
MEDIA_BACKEND=vlc
VLC_HTTP_URL=http://localhost:8080
VLC_HTTP_PASSWORD=your_password
```

The VLC web interface must be enabled and configured with the corresponding password.

### 6. Run the Application

```bash
python main.py
```

Once the application starts, say `ASSISTANT` followed by a supported multimedia command.

Press `Ctrl+C` to stop the application.

## Testing

The project includes automated tests to verify the functionality of its individual modules and multimedia control operations.

Testing can be executed using:

```bash
python -m pytest -q
```

The test suite is used to check application behaviour, command processing, media controls and error-handling scenarios.

## Project Deliverables

All project deliverables and required documentation are available in the [`reports/`](reports/) folder.

This includes the Software Requirements Specification (SRS), Software Architecture and Design (SAD) document, test plan, unit testing report, system integration testing report, code coverage report and other supporting project documentation.

## Implementation Note

This project is implemented entirely as a software application. It uses the computer's microphone and software-based multimedia control interfaces. It does not require Raspberry Pi, ESP32, external hardware modules, sensors or camera-based gesture recognition.
