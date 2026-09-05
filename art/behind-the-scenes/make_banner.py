"""Render banner_ascii.txt (400x122 chars) to banner.png for the README.
Three ink classes from the game palette: light strokes slate, mid cyan, heavy acid.
Run: python make_banner.py   (from this folder)"""
from PIL import Image, ImageDraw, ImageFont

rows = open("banner_ascii.txt", encoding="utf-8").read().rstrip("\n").splitlines()
font = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 11)
cw, ch = font.getbbox("@")[2], 13            # consolas is monospace: one advance fits all
W, H = cw * max(map(len, rows)), ch * len(rows)
img = Image.new("RGB", (W + 16, H + 16), (10, 14, 31))          # NIGHT
draw = ImageDraw.Draw(img)
INK = {".:-": (74, 85, 104), "=+*": (53, 198, 244), "#%@": (198, 240, 42)}   # SLATE, CYAN, ACID
for y, row in enumerate(rows):
    for chars, color in INK.items():
        layer = "".join(c if c in chars else " " for c in row)
        if layer.strip():
            draw.text((8, 8 + y * ch), layer, font=font, fill=color)
img.save("banner.png", optimize=True)
print("banner.png", img.size)
