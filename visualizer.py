# visualizer.py
import pygame, time, math
from config import *

# ------- Styling -------
NOTE_COLORS = {
    WAVE_SINE:  (90, 180, 255),
    WAVE_SQUARE:(255, 160, 90),
    WAVE_SAW:   (180, 255, 120),
}
WHITE = (238,238,238)
BLACK = (28,28,28)
GREY  = (92,92,92)
BG    = (16,16,16)
RED   = (225,70,70)
CARD  = (24,24,24)
OUTL  = (54,54,54)

# ------- Layout (tweak freely) -------
TOP_BAR_H   = 16
TOP_PAD     = 18
BOTTOM_PAD  = 22
KEY_W       = 30
KEY_H       = 98
ROW_GAP     = 18    # gap between lower & upper rows
KEY_GAP     = 5
CARD_PAD    = 16

class Visualizer:
    """Reactive UI with: top level meter, centered two-row keyboard card, bottom status."""
    def __init__(self, surface, keymap):
        self.surf = surface
        self.keymap = keymap
        self.active = {}  # keycode -> dict(start, freq, wave, volume, release?)
        self.last_frame_time = time.time()
        self.fps_smooth = 60.0

        # dynamic geometry (computed on resize/init)
        self._compute_layout()

    def set_keymap(self, keymap):
        self.keymap = keymap
        # positions depend on width; keep the same layout (no need to recompute rows)

    # ---------- Public hooks ----------
    def note_on(self, key, freq, wave, volume):
        now = time.time()
        self.active[key] = {
            "start": now, "freq": freq, "wave": wave,
            "volume": volume
        }

    def note_off(self, key):
        if key in self.active:
            self.active[key]["release"] = time.time()

    def sustain_flush(self, keys):
        for k in keys:
            self.note_off(k)

    # ---------- Frame update & draw ----------
    def update(self):
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now
        self.fps_smooth = 0.92*self.fps_smooth + 0.08*(1.0/max(1e-5, dt))

        # remove visuals after release + ENV_RELEASE
        to_del = []
        for k, ev in self.active.items():
            rel = ev.get("release")
            if rel and (now - rel) > (ENV_RELEASE * 1.2):
                to_del.append(k)
        for k in to_del:
            self.active.pop(k, None)

    def draw(self, octave, wave, volume, sustain, rec_on, status_msg=""):
        w, h = self.surf.get_size()
        # If window changed, recompute geometry once
        if (w, h) != (self._w, self._h):
            self._compute_layout()

        self.surf.fill(BG)
        self._draw_top_meter()
        self._draw_keyboard_card()
        self._draw_status(octave, wave, volume, sustain, rec_on, status_msg)

        pygame.display.flip()

    # ---------- Geometry ----------
    def _compute_layout(self):
        self._w, self._h = self.surf.get_size()

        # Keyboard card rect (centered horizontally)
        kb_total_h = KEY_H * 2 + ROW_GAP  # two rows plus gap
        kb_card_h = kb_total_h + CARD_PAD*2
        kb_card_y = TOP_PAD + TOP_BAR_H + 10
        kb_card_w = min(self._w - 32, 12*(KEY_W + KEY_GAP) + 20)
        kb_card_x = (self._w - kb_card_w) // 2
        self.kb_card = pygame.Rect(kb_card_x, kb_card_y, kb_card_w, kb_card_h)

        # Row baselines inside the card
        self.lower_y = self.kb_card.y + CARD_PAD
        self.upper_y = self.lower_y + KEY_H + ROW_GAP

        # Left anchor so keyboard is centered within the card
        # Layout uses 10 white keys per row
        total_white = 10
        kb_width = total_white * KEY_W + (total_white-1)*KEY_GAP
        self.kb_left = self.kb_card.x + (self.kb_card.w - kb_width)//2

        # Precompute rectangles for positions
        self.rows = self._compute_rows_positions()

        # Status text baseline (always BELOW the keyboard card)
        self.status_y = self.kb_card.bottom + BOTTOM_PAD

    # ---------- Drawing pieces ----------
    def _draw_top_meter(self):
        # blend color by active waves & amplitude
        total_amp, mix = 0.0, [0,0,0]
        for ev in self.active.values():
            a = ev["volume"]; total_amp += a
            c = NOTE_COLORS.get(ev["wave"], (200,200,200))
            mix[0]+=c[0]*a; mix[1]+=c[1]*a; mix[2]+=c[2]*a
        col = (int(mix[0]/total_amp), int(mix[1]/total_amp), int(mix[2]/total_amp)) if total_amp>0 else GREY

        bg = pygame.Rect(16, TOP_PAD, self._w-32, TOP_BAR_H)
        pygame.draw.rect(self.surf, (40,40,40), bg, border_radius=8)
        fill = bg.copy()
        fill.width = int(bg.width * min(1.0, total_amp * 0.9))
        pygame.draw.rect(self.surf, col, fill, border_radius=8)

    def _draw_keyboard_card(self):
        # card
        pygame.draw.rect(self.surf, CARD, self.kb_card, border_radius=14)
        pygame.draw.rect(self.surf, OUTL, self.kb_card, width=1, border_radius=14)

        # lower & upper rows (whites first, then blacks for layering)
        self._draw_row(self.lower_y, lower=True)
        self._draw_row(self.upper_y, lower=False)

        # active glow overlays
        breath = 0.55 + 0.45*math.sin(time.time()*7.5)
        for keycode, ev in self.active.items():
            pos = self.rows.get(keycode)
            if not pos: continue
            x,y,is_black = pos
            col = NOTE_COLORS.get(ev["wave"], (220,220,220))
            alpha = int(110 + 145*breath*ev["volume"])
            s = pygame.Surface((KEY_W, KEY_H if not is_black else KEY_H//2), pygame.SRCALPHA)
            pygame.draw.rect(s, (*col, max(60, alpha)), s.get_rect(), border_radius=6)
            self.surf.blit(s, (x, y))
            # thin accent line
            thin = pygame.Surface((KEY_W, 3), pygame.SRCALPHA)
            thin.fill((*col, 200))
            self.surf.blit(thin, (x, y + (KEY_H if not is_black else KEY_H//2) - 6))

    def _draw_row(self, y, lower=True):
        # White keys
        for i in range(10):
            x = self.kb_left + i*(KEY_W+KEY_GAP)
            pygame.draw.rect(self.surf, WHITE, (x,y,KEY_W,KEY_H), border_radius=6)
            pygame.draw.rect(self.surf, OUTL,  (x,y,KEY_W,KEY_H), width=1, border_radius=6)
        # Black keys (positions 0,1,3,4,5)
        black_slots = [0,1,3,4,5]
        base_y = y - 2
        for idx in black_slots:
            x = self.kb_left + idx*(KEY_W+KEY_GAP) + KEY_W - KEY_W//3
            pygame.draw.rect(self.surf, BLACK, (x,base_y,KEY_W,KEY_H//2), border_radius=6)
            pygame.draw.rect(self.surf, OUTL,  (x,base_y,KEY_W,KEY_H//2), width=1, border_radius=6)

    def _draw_status(self, octave, wave, volume, sustain, rec_on, status_msg):
        font = pygame.font.SysFont(None, 22)
        info = f"Octave {octave} | Wave {['Sine','Square','Saw'][wave]} | Vol {volume:.2f} | Sustain {'ON' if sustain else 'OFF'} | FPS {self.fps_smooth:,.0f}"
        img  = font.render(info, True, (230,230,230))
        self.surf.blit(img, (16, self.status_y))

        # right-aligned REC and message
        if rec_on:
            rec = font.render("REC ●", True, RED)
            rw = rec.get_width()
            self.surf.blit(rec, (self._w - 16 - rw, self.status_y))
        if status_msg:
            sm = font.render(status_msg, True, (180,220,180))
            self.surf.blit(sm, (16, self.status_y + 24))

    # ---------- Key positions (for highlighting) ----------
    def _compute_rows_positions(self):
        rows = {}

        # Lower row: Z X C V B N M , . /
        lower_white_order = ['z','x','c','v','b','n','m',',','.','/']
        # Upper row:  Q W E R T Y U I O P
        upper_white_order = ['q','w','e','r','t','y','u','i','o','p']

        # Whites
        for i, k in enumerate(lower_white_order):
            x = self.kb_left + i*(KEY_W+KEY_GAP)
            rows[ord(k)] = (x, self.lower_y, False); rows[ord(k.upper())]=(x, self.lower_y, False)
        for i, k in enumerate(upper_white_order):
            x = self.kb_left + i*(KEY_W+KEY_GAP)
            rows[ord(k)] = (x, self.upper_y, False); rows[ord(k.upper())]=(x, self.upper_y, False)

        # Blacks over gaps
        def lower_black_x(i):  # 0,1,3,4,5
            return self.kb_left + i*(KEY_W+KEY_GAP) + KEY_W - KEY_W//3

        # lower blacks: s d g h j
        for k, i in {'s':0, 'd':1, 'g':3, 'h':4, 'j':5}.items():
            rows[ord(k)] = (lower_black_x(i), self.lower_y - 2, True)
            rows[ord(k.upper())] = rows[ord(k)]

        # upper blacks: 2 3 5 6 7
        for k, i in {'2':0, '3':1, '5':3, '6':4, '7':5}.items():
            rows[ord(k)] = (lower_black_x(i), self.upper_y - 2, True)

        return rows
