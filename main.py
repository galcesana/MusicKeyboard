import pygame
import numpy as np
import time
import wave
import datetime
from collections import defaultdict

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

# ---------------------- Key -> Note mapping ----------------------
LOWER_WHITE = ['Z','X','C','V','B','N','M',',','.','/']   # C D E F G A B C D E
LOWER_BLACK_POS = {'S':'C#', 'D':'D#', 'G':'F#', 'H':'G#', 'J':'A#'}
UPPER_WHITE = ['Q','W','E','R','T','Y','U','I','O','P']   # C D E F G A B C D E
UPPER_BLACK_POS = {'2':'C#', '3':'D#', '5':'F#', '6':'G#', '7':'A#'}

def build_keymap(base_octave):
    km = {}
    white_notes = ['C','D','E','F','G','A','B','C','D','E']
    octs = [base_octave]*7 + [base_octave+1]*3
    for key, name, octv in zip(LOWER_WHITE, white_notes, octs):
        km[ord(key.lower())] = (name, octv); km[ord(key)] = (name, octv)
    for k, name in LOWER_BLACK_POS.items():
        km[ord(k.lower())] = (name, base_octave); km[ord(k)] = km[ord(k.lower())]
    white_notes_up = ['C','D','E','F','G','A','B','C','D','E']
    octs_up = [base_octave+1]*7 + [base_octave+2]*3
    for key, name, octv in zip(UPPER_WHITE, white_notes_up, octs_up):
        km[ord(key.lower())] = (name, octv); km[ord(key)] = (name, octv)
    for k, name in UPPER_BLACK_POS.items():
        km[ord(k)] = (name, base_octave+1); km[ord(k.lower())] = (name, base_octave+1)
    return km

# ---------------------- Recording ----------------------
class Recorder:
    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.is_recording = False
        self.start_time = None
        self.events = []  # dicts with start, end, freq, wave, volume
        self.active = {}  # key -> event

    def start(self):
        self.is_recording = True
        self.start_time = time.time()
        self.events.clear()
        self.active.clear()

    def stop(self):
        if not self.is_recording:
            return None
        now = time.time()
        for ev in self.events:
            if ev['end'] is None:
                ev['end'] = now
        self.is_recording = False
        return self.render_to_wav()

    def note_on(self, key, freq, wave, volume):
        if not self.is_recording:
            return
        now = time.time()
        ev = {'start': now, 'end': None, 'freq': float(freq),
              'wave': int(wave), 'volume': float(volume)}
        self.events.append(ev)
        self.active[key] = ev

    def note_off(self, key):
        if not self.is_recording:
            return
        now = time.time()
        ev = self.active.get(key)
        if ev and ev['end'] is None:
            ev['end'] = now
        self.active.pop(key, None)

    def sustain_flush(self, keys_to_close):
        if not self.is_recording:
            return
        now = time.time()
        for key in keys_to_close:
            ev = self.active.get(key)
            if ev and ev['end'] is None:
                ev['end'] = now
                self.active.pop(key, None)

    def render_to_wav(self):
        if not self.events:
            return None
        rel_events = []
        for ev in self.events:
            start = max(0.0, ev['start'] - self.start_time)
            end = max(start + 0.001, ev['end'] - self.start_time if ev['end'] else start + 0.001)
            rel_events.append({**ev, 'start': start, 'end': end})
        total_duration = max(e['end'] + ENV_RELEASE for e in rel_events)
        total_samples = int(self.sample_rate * total_duration) + 1
        mix = np.zeros(total_samples, dtype=np.float32)
        for ev in rel_events:
            dur = max(0.001, (ev['end'] - ev['start']) + ENV_RELEASE)
            note = synth_note(ev['wave'], ev['freq'], dur, ev['volume'])
            start_idx = int(ev['start'] * self.sample_rate)
            end_idx = start_idx + len(note)
            if end_idx > len(mix):
                mix = np.pad(mix, (0, end_idx - len(mix)), mode='constant')
            mix[start_idx:end_idx] += note
        peak = np.max(np.abs(mix)) if np.max(np.abs(mix)) > 0 else 1.0
        if peak > 1.0:
            mix = mix / peak
        int16 = (mix * 32767).astype(np.int16)
        stereo = np.column_stack((int16, int16))
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{ts}.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(stereo.tobytes())
        return filename

# ---------------------- Main ----------------------
def main():
    global sustain_on
    pygame.mixer.pre_init(SAMPLE_RATE, BITSIZE, CHANNELS, AUDIO_BUFFER)
    pygame.init()
    screen = pygame.display.set_mode((820, 240))
    pygame.display.set_caption("Keyboard Piano 🎹  [Space: sustain | [: octave- | ]: octave+ | 1/2/3: wave | +/-: volume | R: rec | Esc: panic]")
    font = pygame.font.SysFont(None, 22)

    current_octave = BASE_OCTAVE
    current_wave = WAVE_SINE
    volume = DEFAULT_VOLUME
    pygame.mixer.set_num_channels(64)

    keymap = build_keymap(current_octave)
    recorder = Recorder()

    running = True
    last_space_time = 0
    space_tap_threshold = 0.2

    def draw_ui(status_msg=""):
        screen.fill((18,18,18))
        txt = f"Octave: {current_octave} | Wave: {['Sine','Square','Saw'][current_wave]} | Volume: {volume:.2f} | Sustain: {'ON' if sustain_on else 'OFF'}"
        img = font.render(txt, True, (240,240,240))
        screen.blit(img, (16, 70))
        rec_txt = "REC ●" if recorder.is_recording else "REC ○"
        rec_color = (220, 80, 80) if recorder.is_recording else (180, 180, 180)
        rec_img = font.render(rec_txt, True, rec_color)
        screen.blit(rec_img, (16, 100))
        if status_msg:
            sm = font.render(status_msg, True, (180,220,180))
            screen.blit(sm, (16, 130))
        hint = "[Space] sustain | [ / ] octave | 1/2/3 wave | +/- volume | R record | Esc panic"
        hint_img = font.render(hint, True, (180,180,180))
        screen.blit(hint_img, (16, 160))
        pygame.display.flip()

    status = ""
    draw_ui(status)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if recorder.is_recording:
                    path = recorder.stop()
                    status = f"Saved: {path}" if path else "Nothing to save."
                running = False

            elif event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_ESCAPE:
                    pygame.mixer.stop()
                    active_channels.clear()
                    held_keys.clear()
                    if recorder.is_recording:
                        recorder.sustain_flush(list(recorder.active.keys()))
                    status = "PANIC!"
                    draw_ui(status)
                    continue
                if key == pygame.K_LEFTBRACKET:
                    current_octave = max(MIN_OCTAVE, current_octave - 1)
                    keymap = build_keymap(current_octave); status = "Octave -"; draw_ui(status); continue
                if key == pygame.K_RIGHTBRACKET:
                    current_octave = min(MAX_OCTAVE, current_octave + 1)
                    keymap = build_keymap(current_octave); status = "Octave +"; draw_ui(status); continue
                if key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    current_wave = {pygame.K_1:WAVE_SINE, pygame.K_2:WAVE_SQUARE, pygame.K_3:WAVE_SAW}[key]
                    status = f"Wave: {['Sine','Square','Saw'][current_wave]}"; draw_ui(status); continue
                if key in (pygame.K_PLUS, pygame.K_EQUALS):
                    volume = min(1.0, volume + 0.05); status = f"Volume: {volume:.2f}"; draw_ui(status); continue
                if key in (pygame.K_MINUS,):
                    volume = max(0.05, volume - 0.05); status = f"Volume: {volume:.2f}"; draw_ui(status); continue
                if key == pygame.K_SPACE:
                    now = time.time()
                    if now - last_space_time < space_tap_threshold:
                        sustain_on = not sustain_on
                        status = f"Sustain: {'ON' if sustain_on else 'OFF'}"
                        if not sustain_on:
                            keys_to_close = [k for k in list(active_channels.keys()) if k not in held_keys]
                            recorder.sustain_flush([k for k in list(recorder.active.keys()) if k not in held_keys])
                            for k in keys_to_close:
                                ch = active_channels.get(k)
                                if ch:
                                    ch.fadeout(int(ENV_RELEASE*1000))
                                    active_channels.pop(k, None)
                    last_space_time = now
                    draw_ui(status); continue
                if key == pygame.K_r:
                    if recorder.is_recording:
                        path = recorder.stop(); status = f"Saved: {path}" if path else "Nothing to save."
                    else:
                        recorder.start(); status = "Recording..."
                    draw_ui(status); continue
                if key in keymap:
                    held_keys.add(key)
                    name, octv = keymap[key]
                    midi = note_name_to_midi(name, octv)
                    freq = midi_to_freq(midi)
                    snd = gen_waveform(current_wave, freq)
                    ch = snd.play(loops=-1)
                    if ch: ch.set_volume(volume); active_channels[key] = ch
                    recorder.note_on(key, freq, current_wave, volume)

            elif event.type == pygame.KEYUP:
                key = event.key
                if key == pygame.K_SPACE:
                    draw_ui(status); continue
                if key in held_keys:
                    held_keys.discard(key)
                    ch = active_channels.get(key)
                    if ch:
                        if sustain_on: pass
                        else: ch.fadeout(int(ENV_RELEASE*1000)); active_channels.pop(key, None)
                    if not sustain_on:
                        recorder.note_off(key)

        if not sustain_on:
            for k in list(active_channels.keys()):
                if k not in held_keys:
                    ch = active_channels.get(k)
                    if ch and not ch.get_queue():
                        ch.fadeout(int(ENV_RELEASE*1000))
                        active_channels.pop(k, None)
        draw_ui(status)

    pygame.quit()

if __name__ == "__main__":
    main()
