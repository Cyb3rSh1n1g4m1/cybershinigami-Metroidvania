"""Headless verification of the badge app on the official simulator.

Runs badge_simulator with SDL's dummy video driver, a FAKE clock (16ms per
frame, so 30 simulated seconds take a moment of wall time and timing is
deterministic), synthetic key events on a schedule, and framebuffer
screenshots at chosen frames. Any exception in the app surfaces as a normal
traceback. Run from the badger/home clone:

    cd D:/Projects/badger-home
    python D:/Projects/Cybershinigami/badge/sim_headless.py
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
SHOTS = os.path.abspath("shots")
os.makedirs(SHOTS, exist_ok=True)
sys.argv = ["badge_simulator.py", "badge/apps/cybershinigami", "--screenshots", SHOTS]
sys.path.insert(0, os.path.join(os.getcwd(), "simulator"))

import pygame  # noqa: E402
import badge_simulator as bs  # noqa: E402

# The simulator's blit rejects Image.window() objects; the real badge blits
# them fine (measured). On the desktop RAM is free, so windows become copies.
def _window_copy(self, x, y, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.blit(self._surface, (0, 0), pygame.Rect(int(x), int(y), int(w), int(h)))
    return bs.Image(_surface=s)


bs.Image.window = _window_copy

FRAME_MS = 16
FRAMES = 60 * 34
_frame = 0
pygame.time.get_ticks = lambda: _frame * FRAME_MS      # deterministic clock

K = {"A": pygame.K_z, "B": pygame.K_x, "C": pygame.K_SPACE}


def sec(s):
    return int(s * 60)


# (frame, key, down?)  — 15s of attract, then a played run exercising every verb
EVENTS = {}
def press(t, key, hold=0.05):
    EVENTS.setdefault(sec(t), []).append((K[key], True))
    EVENTS.setdefault(sec(t + hold), []).append((K[key], False))

press(15.0, "A")                    # demo -> TITLE
press(15.6, "A")                    # START -> PLAY
press(16.2, "B"); press(16.55, "B") # jump, double jump
press(17.4, "A")                    # light cut
press(18.3, "C")                    # dash
press(19.2, "A", hold=0.6)          # hold + release = SIGKILL
press(21.0, "B"); press(22.5, "A"); press(24.0, "C"); press(25.5, "B")
press(26.0, "A", hold=0.6); press(28.0, "B"); press(29.0, "A")

SHOTLIST = {sec(1.0): "attract_title", sec(7.5): "title_late", sec(10.0): "attract_run", sec(12.9): "attract_djump",
            sec(14.1): "attract_dash", sec(15.3): "title_return", sec(11.0): "attract_late",
            sec(16.6): "play_djump", sec(19.5): "play_iai_hold", sec(19.95): "play_sigkill",
            sec(24.05): "play_dash", sec(30.0): "play_late", sec(33.5): "end"}


def run(update_func, fps=60, init=None, on_exit=None):
    global _frame
    if not callable(init):
        mod = sys.modules.get(getattr(update_func, "__module__", None))
        if mod is not None:
            init = getattr(mod, "init", None)
    if callable(init):
        init()
    for f in range(FRAMES):
        _frame = f
        for key, down in EVENTS.get(f, []):
            pygame.event.post(pygame.event.Event(
                pygame.KEYDOWN if down else pygame.KEYUP, key=key, mod=0, unicode=""))
        bs.io.update()
        result = update_func()
        bs.screen.present()
        if f in SHOTLIST:
            pygame.image.save(bs.screen._surface, os.path.join(SHOTS, SHOTLIST[f] + ".png"))
        if result is not None:
            print(f"app returned {result!r} at frame {f}")
            break
    print(f"headless run complete: {_frame + 1} frames, shots in {SHOTS}")
    return None


bs.run = run
bs.main()
