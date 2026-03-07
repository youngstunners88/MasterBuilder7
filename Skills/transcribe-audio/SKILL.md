---
name: transcribe-audio
description: Transcribe audio files to text. Use when user wants to convert speech to text, get transcripts of audio/video files.
metadata:
  author: youngstunners.zo.computer
---

# Transcribe Audio Skill

Transcribes audio and video files to text using Whisper.

## Usage

### Transcribe Audio
```
transcribe_audio(audio_file_path="/path/to/audio.wav")
```

### Transcribe Video
```
transcribe_video(video_file_path="/path/to/video.mp4")
```

## Supported Formats
- Audio: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`
- Video: `.mp4`, `.avi`, `.mov`, `.webm`

## Output
Saves transcript as `.transcript.jsonl` next to source file with:
- Text content
- Speaker segments (if available)
- Timestamps

## Tools
- transcribe_audio: For audio files
- transcribe_video: For video files