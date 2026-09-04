from badgeware import screen, io, brushes, shapes
import st


def spawn(kind, x=None):
    x = st.W + 20 if x is None else x
    if kind == "worm":
        st.enemies.append(["worm", float(x), float(st.GROUND), 2, 0.0])
    else:
        st.enemies.append(["drone", float(x), float(st.GROUND - 46), 2, 0.0])


def hit_box(x, y, w, h, dmg):
    for e in st.enemies:
        ew, eh = (32, 22) if e[0] == "worm" else (24, 20)
        ex, ey = e[1] - ew / 2, e[2] - eh
        if x < ex + ew and x + w > ex and y < ey + eh and y + h > ey:
            e[3] -= dmg
            st.fx.append(["hit", e[1], e[2] - eh / 2, 0.0])


def update(dt):
    r = st.reaper
    k = 2.4 if r.dash > 0.0 else 1.0
    st.world_x += st.speed * dt * k
    for e in st.enemies:
        e[1] -= st.speed * dt * k
        e[4] += dt
        if e[0] == "worm":
            e[1] -= 22 * dt
        else:
            ph = (e[4] * 2.2) % 2
            e[2] = st.GROUND - 46 + 5 * (ph if ph < 1 else 2 - ph)
        ew, eh = (32, 22) if e[0] == "worm" else (24, 20)
        if abs(e[1] - r.x) < (ew / 2 + 8) and abs((e[2] - eh / 2) - (r.y - 16)) < (eh / 2 + 12):
            r.take_hit()
    for e in [e for e in st.enemies if e[3] <= 0]:
        st.souls.append([e[1], e[2] - 14, 0.0])
        st.fx.append(["kill", e[1], e[2] - 12, 0.0])
        st.enemies.remove(e)
    st.enemies[:] = [e for e in st.enemies if e[1] > -40]

    for s in st.souls:
        s[2] += dt
        if s[2] > 0.4:
            dx, dy = r.x - s[0], (r.y - 18) - s[1]
            d = max(1.0, (dx * dx + dy * dy) ** 0.5)
            sp = min(260, 80 + s[2] * 220) * dt
            s[0] += dx / d * sp
            s[1] += dy / d * sp
            if d < 8:
                r.souls += 1
                s[2] = -1
        else:
            s[0] -= st.speed * dt
    st.souls[:] = [s for s in st.souls if s[2] >= 0]

    for f in st.fx:
        f[3] += dt
        if f[0] == "crescent":
            f[1] += 170 * dt
            hit_box(f[1] - 12, f[2] - 12, 26, 24, 3)
        else:
            f[1] -= st.speed * dt
    life = {"crescent": 0.32, "kill": 0.3, "dj": 0.25, "hit": 0.15}
    st.fx[:] = [f for f in st.fx if f[3] < life[f[0]]]


def draw():
    screen.brush = st.NIGHT
    screen.clear()
    off = -((st.world_x * 0.5) % st.bg.width)
    x = off
    while x < st.W:
        screen.blit(st.bg, x, st.GROUND - st.bg.height)
        x += st.bg.width
    screen.brush = st.INK
    screen.draw(shapes.rectangle(0, st.GROUND, st.W, st.H - st.GROUND))
    screen.brush = st.CYAN
    screen.draw(shapes.rectangle(0, st.GROUND, st.W, 1))
    screen.brush = st.SLATE
    seg = -(st.world_x % 24)
    while seg < st.W:
        screen.draw(shapes.rectangle(seg, st.GROUND + 6, 12, 1))
        seg += 24

    for s in st.souls:
        screen.blit(st.soul.frame(io.ticks / 90), s[0] - 6, s[1] - 6)
    for e in st.enemies:
        if e[0] == "worm":
            screen.blit(st.worm.frame(io.ticks / 110), e[1] - 16, e[2] - 32)
        else:
            screen.blit(st.drone.frame(io.ticks / 90), e[1] - 12, e[2] - 24)
    st.reaper.draw()
    for f in st.fx:
        if f[0] == "crescent":
            screen.blit(st.crescent.frame(f[3] * 12), f[1] - 16, f[2] - 16)
        elif f[0] == "kill":
            screen.brush = st.ACID
            screen.draw(shapes.circle(f[1], f[2], 2 + f[3] * 60).stroke(2))
        elif f[0] == "dj":
            screen.brush = brushes.color(53, 198, 244, int(200 * (1 - f[3] / 0.25)))
            screen.draw(shapes.circle(f[1], f[2], 4 + f[3] * 40).stroke(1))
        else:
            screen.brush = st.WHITE
            screen.draw(shapes.circle(f[1], f[2], 3 + f[3] * 30).stroke(1))


def hud(hiscore):
    screen.font = st.font_small
    for i in range(3):
        screen.brush = st.CYAN if i < st.reaper.integrity else st.SLATE
        screen.draw(shapes.rectangle(4 + i * 9, 4, 7, 4))
    screen.brush = st.ACID
    screen.text("$%d" % st.reaper.souls, 4, 10)
    screen.brush = st.SHADOW
    screen.text("HI %d" % hiscore, st.W - 38, 5)
    screen.brush = st.WHITE
    screen.text("HI %d" % hiscore, st.W - 39, 4)


def center(text, y):
    w, _ = screen.measure_text(text)
    screen.text(text, 80 - w // 2, y)
