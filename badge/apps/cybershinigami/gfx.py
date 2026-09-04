import gc
from badgeware import Image, PixelFont
import st

# player sheet index: (first cell, count), 6 cells per row. Must match
# build_assets.py's PLAYER order.
P = {"run": (0, 4), "attack": (4, 2), "jump": (6, 2), "fall": (8, 1),
     "dash": (9, 1), "heavy": (10, 2), "double_jump": (12, 1), "hurt": (13, 1),
     "death": (14, 1), "iai": (15, 2), "land": (17, 1)}


class Anim:
    # Measured on the badge: a window costs ~736 bytes. 48 cached windows were
    # 35KB of the ~150KB heap, so only the player's frames stay resident;
    # enemy/effect frames are windowed per blit and garbage-collected.
    def __init__(self, img, cw, ch, cols, start, n, cache):
        self.img, self.cw, self.ch, self.cols, self.start, self.n = img, cw, ch, cols, start, n
        self.cache = [self._win(i) for i in range(n)] if cache else None

    def _win(self, i):
        k = self.start + i
        return self.img.window((k % self.cols) * self.cw, (k // self.cols) * self.ch,
                               self.cw, self.ch)

    def frame(self, i):
        i = int(i) % self.n
        return self.cache[i] if self.cache else self._win(i)


def strip(path, cw, ch, n):
    img = Image.load(path)
    st.sheets.append(img)
    return Anim(img, cw, ch, n, 0, n, False)


def load():
    gc.collect()
    sheet = Image.load("assets/player.png")     # biggest first, heap contiguous
    st.sheets.append(sheet)
    for name, (start, n) in P.items():
        st.anim[name] = Anim(sheet, st.CELL, st.CELL, 6, start, n, True)
    gc.collect()
    st.bg = Image.load("assets/bg_far.png")
    gc.collect()
    # one font, loaded before the small strips: it is required, they degrade
    st.font_small = PixelFont.load("/system/assets/fonts/nope.ppf")
    st.font_big = st.font_small
    gc.collect()
    st.worm = strip("assets/worm.png", 32, 32, 4)
    st.drone = strip("assets/drone.png", 24, 24, 3)
    st.soul = strip("assets/soul.png", 12, 12, 4)
    st.crescent = strip("assets/crescent.png", 32, 32, 4)
    st.logo = Image.load("assets/logo.png")
    st.title_bg = Image.load("assets/title_bg.png")   # 160x120 paletted, ~19KB
    gc.collect()
