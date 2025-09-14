from config import *
import time
import numpy as np
import wave
import datetime 
from utils import synth_note

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