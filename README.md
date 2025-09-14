# Keyboard Piano

Turn your **computer keyboard** into a mini piano 🎹 — no MIDI keyboard required.

## Features

- Play notes with your typing keyboard (Z-row + Q-row)
- **Sustain** (hold or toggle with Space)
- **Octave shift**: `[` down, `]` up (C3–C6)
- **Waveforms**: `1` = Sine, `2` = Square, `3` = Saw
- **Volume**: `-` down, `+` up
- **Panic** (stop all sounds): `Esc`
- Simple **ADSR**-style fadeout via channel fade
- Works offline; **no audio files needed**

## Quick start

```bash
# 1) Create a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run
python keyboard_piano.py
```

When the window is focused, press keys to play.

## Key mapping (lower row = lower octave)

White keys (lower octave):

```
Z  X  C  V  B  N  M  ,  .  /
C  D  E  F  G  A  B  C  D  E
```

Black keys (accidentals):

```
   S  D     G  H  J
   C# D#    F# G# A#
```

Higher octave on the Q row:

```
Q  W  E  R  T  Y  U  I  O  P
C  D  E  F  G  A  B  C  D  E
and
  2  3     5  6  7   -> sharps (C#, D#, F#, G#, A#)
```

## Controls

- Sustain **hold**: hold `Space`
- Sustain **toggle**: tap `Space` quickly
- Octave: `[` (down), `]` (up)
- Waveform: `1` (sine), `2` (square), `3` (saw)
- Volume: `-` / `+`
- Panic (stop all): `Esc`
- **Recording**: `Tab` (start/stop recording)

## Notes

- For minimal latency, close heavy background apps. On Windows, use Python 3.11+ if possible.
- This app uses `pygame.mixer` with a small buffer to reduce latency. If you hear crackles, increase `AUDIO_BUFFER` in the script.

## License

MIT

---

## New: Recording to WAV

- Press **Tab** to **start/stop recording**. While recording, you'll see `REC ●` in red.
- When you stop, a file like `recording_YYYYmmdd_HHMMSS.wav` is saved in the current folder.
- The recorder logs note events (start/end, pitch, waveform, volume) and renders an offline mix, so it's clean and free of system noise.
- Sustain is respected: if you release a key while sustain is ON, the note ends when you toggle sustain OFF.
