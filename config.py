# ---------------------- Config ----------------------
SAMPLE_RATE = 44100
BITSIZE = -16          # 16-bit signed
CHANNELS = 2
AUDIO_BUFFER = 256     # smaller = lower latency, but risk crackles
BASE_OCTAVE = 4        # starting octave (C4 = middle C)
MIN_OCTAVE = 3
MAX_OCTAVE = 6
DEFAULT_VOLUME = 0.6

WAVE_SINE = 0
WAVE_SQUARE = 1
WAVE_SAW = 2

# Envelope (used both for live and offline rendering)
ENV_ATTACK = 0.005
ENV_DECAY = 0.08
ENV_SUSTAIN = 0.85
ENV_RELEASE = 0.12  # live fadeout approximates this

# Simple cache for generated sounds: (wave, freq) -> pygame.Sound
sound_cache = {}

# Track which keys are currently sustained/held
active_channels = {}        # key -> pygame.Channel
sustain_on = False
held_keys = set()
