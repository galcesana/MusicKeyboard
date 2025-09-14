import pygame
import numpy as np
from config import *

# ---------------------- Utility ----------------------
def midi_to_freq(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))  # MIDI 69 = A4 = 440 Hz

def note_name_to_midi(name, octave):
    names = {'C':0, 'C#':1, 'D':2, 'D#':3, 'E':4, 'F':5, 'F#':6,
             'G':7, 'G#':8, 'A':9, 'A#':10, 'B':11}
    return 12 * (octave + 1) + names[name]

def apply_envelope(wave, sample_rate, attack, decay, sustain_level, release):
    env = np.ones_like(wave)
    a_samps = max(1, int(attack * sample_rate))
    d_samps = max(1, int(decay * sample_rate))
    r_samps = max(1, int(release * sample_rate))
    env[:a_samps] = np.linspace(0, 1, a_samps)
    env[a_samps:a_samps+d_samps] = np.linspace(1, sustain_level, d_samps)
    sustain_start = a_samps + d_samps
    sustain_end = len(env) - r_samps
    if sustain_end > sustain_start:
        env[sustain_start:sustain_end] = sustain_level
    env[sustain_end:] = np.linspace(sustain_level, 0, len(env)-sustain_end)
    return wave * env

def gen_waveform(wave_type, freq, duration=2.5):
    key = (wave_type, round(freq, 4), duration)
    if key in sound_cache:
        return sound_cache[key]
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    if wave_type == WAVE_SINE:
        wave = np.sin(2*np.pi*freq*t)
    elif wave_type == WAVE_SQUARE:
        wave = np.sign(np.sin(2*np.pi*freq*t))
    else:
        wave = 2.0 * (t*freq - np.floor(0.5 + t*freq))
    wave = apply_envelope(wave, SAMPLE_RATE, ENV_ATTACK, ENV_DECAY, ENV_SUSTAIN, 0.4)
    wave = (wave * 32767).astype(np.int16)
    stereo = np.column_stack((wave, wave))
    sound = pygame.sndarray.make_sound(stereo.copy())
    sound_cache[key] = sound
    return sound

def synth_note(wave_type, freq, duration, volume=1.0):
    n_samps = max(1, int(SAMPLE_RATE * duration))
    t = np.linspace(0, duration, n_samps, endpoint=False)
    if wave_type == WAVE_SINE:
        wave = np.sin(2*np.pi*freq*t)
    elif wave_type == WAVE_SQUARE:
        wave = np.sign(np.sin(2*np.pi*freq*t))
    else:
        wave = 2.0 * (t*freq - np.floor(0.5 + t*freq))
    wave = apply_envelope(wave, SAMPLE_RATE, ENV_ATTACK, ENV_DECAY, ENV_SUSTAIN, ENV_RELEASE)
    return (wave * volume).astype(np.float32)