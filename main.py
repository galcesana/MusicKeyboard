import pygame
import time
from utils import *
from config import *
from piano_mapping import *
from recording import Recorder
from visualizer import Visualizer  # NEW

# ---------------------- Main ----------------------
def main():
    global sustain_on
    pygame.mixer.pre_init(SAMPLE_RATE, BITSIZE, CHANNELS, AUDIO_BUFFER)
    pygame.init()
    # a bit wider & taller
    screen = pygame.display.set_mode((920, 440))
    pygame.display.set_caption("Keyboard Piano 🎹  [Space: sustain | [: octave- | ]: octave+ | 1/2/3: wave | +/-: volume | Tab: rec | Esc: panic]")
    clock = pygame.time.Clock()

    current_octave = BASE_OCTAVE
    current_wave = WAVE_SINE
    volume = DEFAULT_VOLUME
    pygame.mixer.set_num_channels(64)

    keymap = build_keymap(current_octave)
    recorder = Recorder()
    viz = Visualizer(screen, keymap)

    running = True
    last_space_time = 0
    space_tap_threshold = 0.2

    status = ""

    def draw_ui():
        viz.update()
        viz.draw(current_octave, current_wave, volume, sustain_on, recorder.is_recording, status_msg=status)
        pygame.display.flip()

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
                    draw_ui()
                    continue

                if key == pygame.K_LEFTBRACKET:
                    current_octave = max(MIN_OCTAVE, current_octave - 1)
                    keymap = build_keymap(current_octave)
                    viz.set_keymap(keymap)  # NEW
                    status = "Octave -"
                    draw_ui(); continue

                if key == pygame.K_RIGHTBRACKET:
                    current_octave = min(MAX_OCTAVE, current_octave + 1)
                    keymap = build_keymap(current_octave)
                    viz.set_keymap(keymap)  # NEW
                    status = "Octave +"
                    draw_ui(); continue

                if key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    current_wave = {pygame.K_1:WAVE_SINE, pygame.K_2:WAVE_SQUARE, pygame.K_3:WAVE_SAW}[key]
                    status = f"Wave: {['Sine','Square','Saw'][current_wave]}"
                    draw_ui(); continue

                if key in (pygame.K_PLUS, pygame.K_EQUALS):
                    volume = min(1.0, volume + 0.05)
                    status = f"Volume: {volume:.2f}"
                    draw_ui(); continue

                if key in (pygame.K_MINUS,):
                    volume = max(0.05, volume - 0.05)
                    status = f"Volume: {volume:.2f}"
                    draw_ui(); continue

                if key == pygame.K_SPACE:
                    now = time.time()
                    if now - last_space_time < space_tap_threshold:
                        sustain_on = not sustain_on
                        status = f"Sustain: {'ON' if sustain_on else 'OFF'}"
                        if not sustain_on:
                            keys_to_close = [k for k in list(active_channels.keys()) if k not in held_keys]
                            recorder.sustain_flush([k for k in list(recorder.active.keys()) if k not in held_keys])
                            viz.sustain_flush([k for k in list(viz.active.keys()) if k not in held_keys])  # NEW
                            for k in keys_to_close:
                                ch = active_channels.get(k)
                                if ch:
                                    ch.fadeout(int(ENV_RELEASE*1000))
                                    active_channels.pop(k, None)
                    last_space_time = now
                    draw_ui(); continue

                if key == pygame.K_TAB:
                    if recorder.is_recording:
                        path = recorder.stop(); status = f"Saved: {path}" if path else "Nothing to save."
                    else:
                        recorder.start(); status = "Recording..."
                    draw_ui(); continue

                if key in keymap:
                    held_keys.add(key)
                    name, octv = keymap[key]
                    midi = note_name_to_midi(name, octv)
                    freq = midi_to_freq(midi)
                    snd = gen_waveform(current_wave, freq)
                    ch = snd.play(loops=-1)
                    if ch:
                        ch.set_volume(volume); active_channels[key] = ch
                    recorder.note_on(key, freq, current_wave, volume)
                    viz.note_on(key, freq, current_wave, volume)  # NEW

            elif event.type == pygame.KEYUP:
                key = event.key
                if key == pygame.K_SPACE:
                    draw_ui(); continue
                if key in held_keys:
                    held_keys.discard(key)
                    ch = active_channels.get(key)
                    if ch:
                        if sustain_on:
                            pass
                        else:
                            ch.fadeout(int(ENV_RELEASE*1000))
                            active_channels.pop(key, None)
                    if not sustain_on:
                        recorder.note_off(key)
                        viz.note_off(key)  # NEW

        if not sustain_on:
            for k in list(active_channels.keys()):
                if k not in held_keys:
                    ch = active_channels.get(k)
                    if ch and not ch.get_queue():
                        ch.fadeout(int(ENV_RELEASE*1000))
                        active_channels.pop(k, None)
                    # visual release will fade in viz.update()

        draw_ui()
        clock.tick(90)  # smoother animation with low latency

    pygame.quit()

if __name__ == "__main__":
    main()
