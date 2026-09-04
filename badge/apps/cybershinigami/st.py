# shared state + constants. Small modules compile on a small heap: MicroPython
# compiles each file in RAM, and one 17KB __init__.py failed with MemoryError.
from badgeware import brushes

W, H = 160, 120
GROUND = 98          # the street surface
CELL = 40
FEET = 35            # feet row inside the 40px player cell

speed = 62.0
world_x = 0.0
reaper = None
enemies = []         # [kind, x, y, hp, t]
souls = []           # [x, y, t]
fx = []              # [kind, x, y, t]

anim = {}
worm = drone = soul = crescent = None
bg = logo = title_bg = None
font_big = font_small = None
sheets = []

INK = brushes.color(10, 14, 31)
NIGHT = brushes.color(6, 8, 20)
ACID = brushes.color(198, 240, 42)
CYAN = brushes.color(53, 198, 244)
RED = brushes.color(224, 31, 38)
WHITE = brushes.color(255, 255, 255)
SLATE = brushes.color(74, 85, 104)
SHADOW = brushes.color(0, 0, 0, 120)
PALE = brushes.color(143, 232, 255)
YELLOW = brushes.color(252, 238, 10)
