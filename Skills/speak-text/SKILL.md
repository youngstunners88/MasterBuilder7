---
name: speak-text
description: Convert text to speech/audio files. Use when user wants text read aloud, needs audio output, or wants to generate speech.
metadata:
  author: youngstunners.zo.computer
---

# Speak Text Skill

Converts text to speech audio files.

## Usage

### Generate speech (gTTS - Google TTS)
```python
from gtts import gTTS
tts = gTTS(text="Hello world", lang="en")
tts.save("output.mp3")
```

### Generate speech with pyttsx3 (offline)
```python
import pyttsx3
engine = pyttsx3.init()
engine.say("Hello world")
engine.runAndWait()
```

## Language Options
- "en" - English
- "es" - Spanish  
- "fr" - French
- "de" - German
- "zh" - Chinese
- "ja" - Japanese
- And many more...

## Tools
- run_bash_command: Run Python scripts with gtts or pyttsx3
- Output audio files can be uploaded as assets to zo.space

## Example: Create an audio lesson
```python
from gtts import gTTS

lessons = {
    "lesson1": "Welcome to English Academy. Today we learn basic greetings.",
    "lesson2": "Hello! How are you? I'm fine, thank you!"
}

for name, text in lessons.items():
    tts = gTTS(text=text, lang="en")
    tts.save(f"/home/workspace/audio/{name}.mp3")
```