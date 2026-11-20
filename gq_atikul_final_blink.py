#!/usr/bin/env python3
"""
GQ ATIKUL - Bengali Female Voice Studio - Final (black logo, red eyes, numbers only)

Same female voice as before. New in v5: continuous reading (next line is prepared while the current one plays,
  no gaps) and no "Now Playing" messages.
Earlier:
  - Type  শুরু করো  (or "start") and press Enter: the tool reads ALL lines of
    MY_SCRIPT out loud, one after another, automatically.
Also:
  - Hacker-style banner with colour gradient + boot animation
  - Colour THEME you can change (red / purple / blue / cyan / orange / pink)
  - Your own lines inside MY_SCRIPT (see below)

Setup (Termux):
    pkg install python mpv
    pip install edge-tts
    python gq_atikul_final.py

Commands:
    list          show your lines with numbers
    1, 2, 3 ...   play that line
    all           play all lines one after another
    file x.txt    load lines from a text file (one line = one sentence)
    (or type any text to speak it)
    /voice 1|2  /rate -10  /pitch +3  /vol +0  /save  /show  /theme red   (q = quit)
"""

# ============================================================
#  🎨  CHOOSE YOUR COLOUR:  red, purple, blue, cyan, orange, pink
# ============================================================
THEME = "red"

# ============================================================
#  ✍️  WRITE YOUR OWN LINES HERE  (one line = one sentence)
#  Keep the quotes " " and the comma at the end of each line.
# ============================================================
PAUSE = 0.0   # extra seconds of silence between lines (0 = non-stop)

MY_SCRIPT = [
    "এখানে আপনার নিজের লেখা বসান।",
    "এই লাইনটি মুছে নিজের কথা লিখুন।",
    "আরও লাইন যোগ করতে নতুন লাইনে একইভাবে লিখুন।",
]
# ============================================================

import asyncio
import threading
import random
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    import edge_tts
except ImportError:
    sys.exit("Install first:  pip install edge-tts")

X, B = "\033[0m", "\033[1m"


def c256(n):
    return f"\033[38;5;{n}m"


# 256-colour gradients for the 6 banner lines (top -> bottom)
THEMES = {
    "red":    [196, 160, 124, 88, 52, 240],
    "purple": [201, 165, 129, 93, 57, 240],
    "blue":   [51, 45, 39, 33, 27, 240],
    "cyan":   [123, 87, 51, 45, 39, 240],
    "orange": [214, 208, 202, 166, 130, 240],
    "pink":   [219, 213, 207, 201, 165, 240],
}
ACCENT = {"red": 196, "purple": 177, "blue": 39, "cyan": 51, "orange": 208, "pink": 213}

LOGO = [
    "  ██████╗  ██████╗      █████╗ ████████╗██╗██╗  ██╗██╗   ██╗██╗     ",
    " ██╔════╝ ██╔═══██╗    ██╔══██╗╚══██╔══╝██║██║ ██╔╝██║   ██║██║     ",
    " ██║  ███╗██║   ██║    ███████║   ██║   ██║█████╔╝ ██║   ██║██║     ",
    " ██║   ██║██║▄▄ ██║    ██╔══██║   ██║   ██║██╔═██╗ ██║   ██║██║     ",
    " ╚██████╔╝╚██████╔╝    ██║  ██║   ██║   ██║██║  ██╗╚██████╔╝███████╗",
    "  ╚═════╝  ╚══▀▀═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝",
]

theme = THEME if THEME in THEMES else "red"


def accent():
    return c256(ACCENT[theme])


GLITCH = "▓▒░█▄▀#@%&01"
FILL, EDGE = 235, 252   # letter colour (near-black) and its light outline
EYE_OPEN = [
    "   ▄▄██████▄▄   ",
    " ▄███▀ oo ▀███▄ ",
    " ▀███▄ oo ▄███▀ ",
    "   ▀▀██████▀▀   ",
]
EYE_CLOSED = [
    "                ",
    "                ",
    " ▄▄▄▄▄▄▄▄▄▄▄▄▄▄ ",
    "                ",
]
EYE_GLOW = [52, 88, 124, 160, 196]   # dark red -> bright red
GAP = 22                              # space between the two eyes


def eyes_rows(closed=False, glow=4):
    shape = EYE_CLOSED if closed else EYE_OPEN
    red = c256(EYE_GLOW[glow])
    pupil = c256(226 if glow == 4 else 94)
    w = max(len(l) for l in LOGO)
    pad = " " * max(0, (w - (2 * len(shape[0]) + GAP)) // 2)
    rows = []
    for row in shape:
        cells = "".join(
            f"{pupil}█" if ch == "o" else (f"{red}{ch}" if ch != " " else " ")
            for ch in row
        )
        rows.append(f"{pad}{cells}{X}{' ' * GAP}{cells}{X}")
    return rows


def logo_rows(corrupt=0.0, sweep=-1):
    rows = []
    for idx, line in enumerate(LOGO):
        out = []
        for ch in line:
            if ch == " ":
                out.append(" ")
            elif corrupt and random.random() < corrupt:
                out.append(f"{c256(196)}{random.choice(GLITCH)}")
            else:
                solid = ch in "█▄▀"
                if idx == sweep:
                    col = 196 if solid else 255
                else:
                    col = FILL if solid else EDGE
                out.append(f"{c256(col)}{ch}")
        rows.append("".join(out) + X)
    return rows


def draw(rows, redraw=False):
    if redraw:
        sys.stdout.write(f"\033[{len(rows)}A")
    sys.stdout.write("\n".join(rows) + "\n")
    sys.stdout.flush()


def banner(animate=True):
    print()
    if not animate:
        draw(eyes_rows() + [""] + logo_rows())
        print()
        return
    draw(eyes_rows(closed=True, glow=0) + [""] + logo_rows(corrupt=0.65))
    for amount, glow in ((0.5, 1), (0.35, 2), (0.22, 3), (0.1, 4), (0.04, 4)):
        time.sleep(0.09)
        draw(eyes_rows(glow=glow) + [""] + logo_rows(corrupt=amount), redraw=True)
    for r in range(len(LOGO)):                      # scan line moves down
        time.sleep(0.06)
        draw(eyes_rows() + [""] + logo_rows(sweep=r), redraw=True)
    time.sleep(0.3)                                 # the eyes blink
    draw(eyes_rows(closed=True) + [""] + logo_rows(), redraw=True)
    time.sleep(0.12)
    draw(eyes_rows() + [""] + logo_rows(), redraw=True)
    print()


VOICES = {
    1: ("bn-BD-NabanitaNeural", "Bangladeshi Bengali, female"),
    2: ("bn-IN-TanishaaNeural", "West Bengal Bengali, female"),
}

settings = {"voice": 1, "rate": -8, "pitch": 2, "vol": 0}
TMP = os.path.join(tempfile.gettempdir(), "gq_studio5.mp3")
script = list(MY_SCRIPT)


def fmt(v, unit):
    return f"{v:+d}{unit}"


async def synth(text, path):
    await edge_tts.Communicate(
        text,
        VOICES[settings["voice"]][0],
        rate=fmt(settings["rate"], "%"),
        pitch=fmt(settings["pitch"], "Hz"),
        volume=fmt(settings["vol"], "%"),
    ).save(path)


def play(path):
    """Play an audio file silently and wait until it finishes."""
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if shutil.which("mpv"):
        subprocess.run(["mpv", "--no-video", "--really-quiet", path], check=False, **quiet)
    elif shutil.which("ffplay"):
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                       check=False, **quiet)
    elif shutil.which("termux-media-player"):
        subprocess.run(["termux-media-player", "play", path], check=False, **quiet)
        time.sleep(0.4)
        while True:  # wait until playback ends
            info = subprocess.run(["termux-media-player", "info"],
                                  capture_output=True, text=True).stdout
            if "Playing" not in info:
                break
            time.sleep(0.2)
    else:
        print(f"{c256(226)}[!] Install a player:  pkg install mpv{X}")


def play_all(lines):
    """Read all lines non-stop: the next line is generated while the current one plays."""
    from concurrent.futures import ThreadPoolExecutor

    paths = [os.path.join(tempfile.gettempdir(), f"gq_line_{i}.mp3") for i in range(len(lines))]

    def gen(i):
        asyncio.run(synth(lines[i], paths[i]))

    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(gen, 0)
        for i, line in enumerate(lines):
            fut.result()
            nxt = ex.submit(gen, i + 1) if i + 1 < len(lines) else None
            print(f"{c256(226)}{i + 1}{X}")
            play(paths[i])
            if PAUSE:
                time.sleep(PAUSE)
            fut = nxt
    shutil.copy(paths[-1], TMP)


def speak(text):
    try:
        asyncio.run(synth(text, TMP))
        play(TMP)
    except Exception as e:
        print(f"{c256(196)}[!] Error (check internet): {e}{X}\n")


def show():
    a = accent()
    name, desc = VOICES[settings["voice"]]
    print(f"{a}  Voice : {X}{settings['voice']} - {name} ({desc})")
    print(f"{a}  Rate  : {X}{fmt(settings['rate'], '%')}   "
          f"{a}Pitch : {X}{fmt(settings['pitch'], 'Hz')}   "
          f"{a}Volume: {X}{fmt(settings['vol'], '%')}\n")


def list_script():
    a = accent()
    if not script:
        print(f"{c256(226)}[!] No lines yet. Edit MY_SCRIPT in the code or use: file x.txt{X}\n")
        return
    for i, line in enumerate(script, 1):
        print(f"{a}{i:>3}.{X} {line}")
    print()


def load_file(path):
    global script
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    except OSError as e:
        print(f"{c256(196)}[!] Cannot read file: {e}{X}\n")
        return
    script = lines
    print(f"{accent()}[+] Loaded {len(script)} lines.{X}\n")


def handle_command(cmd):
    global theme
    parts = cmd.split()
    name = parts[0].lower()
    try:
        if name == "/voice" and int(parts[1]) in VOICES:
            settings["voice"] = int(parts[1])
        elif name == "/rate":
            settings["rate"] = max(-50, min(50, int(parts[1])))
        elif name == "/pitch":
            settings["pitch"] = max(-30, min(30, int(parts[1])))
        elif name == "/vol":
            settings["vol"] = max(-50, min(50, int(parts[1])))
        elif name == "/theme":
            if parts[1].lower() in THEMES:
                theme = parts[1].lower()
                banner(animate=False)
            else:
                print(f"{c256(196)}[!] Themes: {', '.join(THEMES)}{X}\n")
                return
        elif name == "/save":
            if not os.path.exists(TMP):
                print(f"{c256(196)}[!] Nothing to save yet.{X}\n")
                return
            out_dir = "/sdcard/Download" if os.path.isdir("/sdcard/Download") else "."
            out = os.path.join(out_dir, f"gq_voice_{int(time.time())}.mp3")
            shutil.copy(TMP, out)
            print(f"{accent()}[+] Saved: {out}{X}\n")
            return
        elif name != "/show":
            print(f"{c256(196)}[!] Unknown command.{X}\n")
            return
        show()
    except (IndexError, ValueError):
        print(f"{c256(196)}[!] Wrong format. Example: /rate -10{X}\n")


class CountOut:
    """Wraps stdout: counts printed lines so we always know where the eyes are."""

    def __init__(self, real):
        self.real = real
        self.lines = 0
        self.lock = threading.RLock()

    def write(self, s):
        with self.lock:
            self.lines += s.count("\n")
            return self.real.write(s)

    def flush(self):
        with self.lock:
            self.real.flush()

    def __getattr__(self, name):
        return getattr(self.real, name)


class EyeBlinker(threading.Thread):
    """Background thread: the eyes blink every few seconds, forever."""

    EYES_TOP = 12   # rows from the prompt up to the first eye row, right after the banner

    def __init__(self, out):
        super().__init__(daemon=True)
        self.out = out
        self.base = out.lines
        self.halt = threading.Event()

    def stop(self):
        self.halt.set()

    def paint(self, closed=False, glow=4):
        rows = eyes_rows(closed=closed, glow=glow)
        with self.out.lock:
            up = self.EYES_TOP + (self.out.lines - self.base)
            if up > shutil.get_terminal_size().lines - 1:
                return False                      # eyes scrolled off the screen
            w = self.out.real.write
            w("\0337")                            # save cursor
            w(f"\033[{up}A")                      # go up to the eyes
            for row in rows:
                w("\r" + row + "\033[K\033[1B")
            w("\0338")                            # back to the prompt
            self.out.real.flush()
        return True

    def run(self):
        while not self.halt.wait(random.uniform(2.0, 4.5)):
            if not self.paint(closed=True):
                continue
            time.sleep(0.13)
            self.paint(closed=False)
            if random.random() < 0.3:             # sometimes a quick double blink
                time.sleep(0.18)
                self.paint(closed=True)
                time.sleep(0.12)
                self.paint(closed=False)


def main():
    out = CountOut(sys.stdout)
    sys.stdout = out
    banner()
    blinker = EyeBlinker(out)
    blinker.start()
    try:
        run_loop()
    finally:
        blinker.stop()


def run_loop():
    while True:
        try:
            text = input(f"{accent()}{B}GQ-ATIKUL{X}{c256(244)}@voice{X}{accent()}:~# {X}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{c256(196)}Bye!{X}")
            break
        low = text.lower()
        if low in ("q", "quit", "exit"):
            print(f"{c256(196)}Bye!{X}")
            break
        if not text:
            continue
        if text.startswith("/"):
            handle_command(text)
        elif low == "list":
            list_script()
        elif low in ("all", "start", "শুরু করো", "শুরু করো।", "শুরু"):
            if not script:
                print(f"{c256(226)}[!] MY_SCRIPT is empty. Write your lines in the code first.{X}\n")
                continue
            try:
                play_all(script)
            except KeyboardInterrupt:
                print(f"\n{c256(196)}[!] Stopped.{X}")
            except Exception as e:
                print(f"{c256(196)}[!] Error (check internet): {e}{X}")
        elif low.startswith("file "):
            load_file(text[5:].strip())
        elif text.isdigit() and 1 <= int(text) <= len(script):
            line = script[int(text) - 1]
            print(f"{c256(226)}{text}{X}")
            speak(line)
        else:
            print(f"{accent()}[*] Generating voice...{X}")
            speak(text)


if __name__ == "__main__":
    main()
