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
