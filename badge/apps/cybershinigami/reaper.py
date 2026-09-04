from badgeware import screen, io
import st
import world


class Inp:
    def __init__(self):
        self.jump = self.dash = self.attack_pressed = self.attack_held = False


class Reaper:
    def __init__(self):
        self.x = 34.0
        self.y = float(st.GROUND)
        self.vy = 0.0
        self.jumps = 0
        self.dash = 0.0
        self.dash_cd = 0.0
        self.attack = 0.0
        self.hold = -1.0
        self.heavy = 0.0
        self.hurt = 0.0
        self.invuln = 0.0
        self.dead = 0.0
        self.integrity = 3
        self.souls = 0
        self.land = 0.0
        self.ghosts = []

    def grounded(self):
        return self.y >= st.GROUND

    def update(self, dt, inp):
        if self.dead > 0.0:
            self.dead += dt
            self.vy += 600 * dt
            self.y = min(st.GROUND, self.y + self.vy * dt)
            return
        self.dash_cd -= dt
        self.invuln -= dt
        self.hurt -= dt
        self.attack -= dt
        self.heavy -= dt
        self.land -= dt

        if self.dash > 0.0:
            self.dash -= dt
            self.ghosts.append((self.x, self.y, 0.0))
            if len(self.ghosts) > 4:
                self.ghosts.pop(0)
        elif inp.dash and self.dash_cd <= 0.0:
            self.dash = 0.18
            self.dash_cd = 0.5
        self.ghosts = [(gx - st.speed * dt, gy, a + dt) for gx, gy, a in self.ghosts if a < 0.25]

        if inp.jump:
            if self.grounded():
                self.vy = -230
                self.jumps = 1
            elif self.jumps < 2:
                self.vy = -215
                self.jumps = 2
                st.fx.append(["dj", self.x, self.y - 10, 0.0])
        if not self.grounded() or self.vy < 0:
            self.vy += (560 if self.vy < 0 else 900) * dt
            self.y += self.vy * dt
            if self.y >= st.GROUND:
                self.y = float(st.GROUND)
                self.vy = 0.0
                self.jumps = 0
                self.land = 0.14
        else:
            self.jumps = 0

        if inp.attack_pressed and self.attack <= 0.0 and self.heavy <= 0.0:
            self.attack = 0.2
            self.hold = 0.0
            world.hit_box(self.x + 8, self.y - 26, 26, 26, 1)
        if self.hold >= 0.0:
            if inp.attack_held:
                self.hold += dt
            else:
                if self.hold >= 0.4 and self.heavy <= 0.0:
                    self.heavy = 0.5
                    st.fx.append(["crescent", self.x + 14, self.y - 22, 0.0])
                self.hold = -1.0

    def take_hit(self):
        if self.invuln > 0.0 or self.dash > 0.0 or self.dead > 0.0:
            return
        self.integrity -= 1
        self.invuln = 1.0
        self.hurt = 0.35
        if self.integrity <= 0:
            self.dead = 0.001
            self.vy = -120

    def frame(self):
        a = st.anim
        t = io.ticks / 1000.0
        if self.dead > 0.0:
            return a["death"].frame(0)
        if self.hurt > 0.0:
            return a["hurt"].frame(0)
        if self.heavy > 0.0:
            return a["heavy"].frame(min(1, (0.5 - self.heavy) * 4))
        if self.hold >= 0.15:
            return a["iai"].frame(t * 4)
        if self.attack > 0.0:
            return a["attack"].frame(min(1, (0.2 - self.attack) * 10))
        if self.dash > 0.0:
            return a["dash"].frame(0)
        if not self.grounded():
            if self.jumps == 2 and self.vy < -60:
                return a["double_jump"].frame(0)
            if self.vy < 0:
                return a["jump"].frame(min(1, (self.vy + 230) / 160))
            return a["fall"].frame(0)
        if self.land > 0.0:
            return a["land"].frame(0)
        return a["run"].frame(t * 9)

    def draw(self):
        g = st.anim["dash"].frame(0)
        for gx, gy, a in self.ghosts:
            g.alpha = int(120 * (1.0 - a / 0.25))
            screen.blit(g, gx - st.CELL // 2, gy - st.FEET)
        g.alpha = 255
        if self.invuln > 0.0 and self.dead <= 0.0 and int(io.ticks / 60) % 2:
            return
        screen.blit(self.frame(), self.x - st.CELL // 2, self.y - st.FEET)
