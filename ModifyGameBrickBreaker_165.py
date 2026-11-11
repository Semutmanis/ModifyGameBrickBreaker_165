import math
import random
import pygame

# ---------- Konfigurasi ----------
WIDTH, HEIGHT = 800, 600
FPS = 60

PADDLE_W, PADDLE_H = 120, 16
PADDLE_SPEED = 10
BALL_R = 9
BASE_SPEED = 6.0
MAX_SPEED = 12.0
MAX_BALLS = 8

ROWS, COLS = 6, 10
GAP = 5
TOP = 70
BRICK_H = 24
TOUGH_CHANCE = 0.25   # brick yang butuh 2 pukulan
DROP_CHANCE = 0.20    # peluang brick pecah menjatuhkan power-up

PADDLE_COLOR = (130, 205, 255)
ELECTRO = (200, 140, 255)

ROW_COLORS = [
    (255, 85, 110), (255, 150, 60), (255, 220, 70),
    (80, 230, 140), (70, 190, 255), (180, 110, 255),
]

# nama, warna, durasi (frame), bobot kemunculan
POWERUPS = {
    "multi": ("x3",     (190, 120, 255), 0,   3),
    "wide":  ("LEBAR",  (80, 200, 255),  600, 3),
    "fast":  ("CEPAT",  (255, 220, 70),  600, 2),
    "slow":  ("LAMBAT", (80, 230, 160),  480, 2),
    "fire":  ("API",    (255, 120, 40),  420, 2),
    "laser": ("LASER",  (255, 70, 70),   480, 2),
    "life":  ("+1",     (255, 90, 120),  0,   1),
}


# ---------- Utilitas umum ----------
def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def glow(surf, pos, radius, color, alpha=70):
    g = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        a = int(alpha * (1 - r / radius) ** 1.5) + 3
        pygame.draw.circle(g, (*color, min(255, a)), (radius, radius), r)
    surf.blit(g, (pos[0] - radius, pos[1] - radius))


def soft_rect_glow(surf, rect, color, spread=12, alpha=55):
    g = pygame.Surface((rect.w + spread * 2, rect.h + spread * 2), pygame.SRCALPHA)
    for i in range(spread, 0, -2):
        a = int(alpha * (1 - i / spread)) + 2
        rr = pygame.Rect(spread - i, spread - i, rect.w + i * 2, rect.h + i * 2)
        pygame.draw.rect(g, (*color, a), rr, border_radius=8 + i)
    surf.blit(g, (rect.x - spread, rect.y - spread))


def draw_heart(surf, x, y, s, color):
    pygame.draw.circle(surf, color, (x - s // 2, y), s // 2 + 1)
    pygame.draw.circle(surf, color, (x + s // 2, y), s // 2 + 1)
    pygame.draw.polygon(surf, color, [(x - s, y + 2), (x + s, y + 2), (x, y + int(s * 1.6))])


def hue_color(h):
    c = pygame.Color(0)
    c.hsva = (h % 360, 70, 100, 100)
    return (c.r, c.g, c.b)


def text_center(surf, font, text, pos, color=(255, 255, 255)):
    img = font.render(text, True, color)
    surf.blit(img, img.get_rect(center=pos))


# ---------- Ikon skill ----------
def draw_icon(surf, kind, cx, cy, s, c=(255, 255, 255)):
    """Gambar ikon skill dengan ukuran setengah-lebar s."""
    w = max(2, int(s * 0.28))
    if kind == "multi":      # satu bola membelah jadi tiga
        pygame.draw.line(surf, c, (cx, cy - s * 0.1), (cx - s * 0.75, cy + s * 0.5), 1)
        pygame.draw.line(surf, c, (cx, cy - s * 0.1), (cx + s * 0.75, cy + s * 0.5), 1)
        pygame.draw.circle(surf, c, (cx, int(cy - s * 0.25)), max(2, int(s * 0.36)))
        pygame.draw.circle(surf, c, (int(cx - s * 0.75), int(cy + s * 0.55)), max(2, int(s * 0.28)))
        pygame.draw.circle(surf, c, (int(cx + s * 0.75), int(cy + s * 0.55)), max(2, int(s * 0.28)))
    elif kind == "wide":     # panah dua arah
        pygame.draw.line(surf, c, (cx - s * 0.8, cy), (cx + s * 0.8, cy), w)
        pygame.draw.polygon(surf, c, [(cx - s, cy), (cx - s * 0.45, cy - s * 0.5), (cx - s * 0.45, cy + s * 0.5)])
        pygame.draw.polygon(surf, c, [(cx + s, cy), (cx + s * 0.45, cy - s * 0.5), (cx + s * 0.45, cy + s * 0.5)])
    elif kind == "fast":     # dua chevron >>
        for off in (-0.55, 0.1):
            pts = [(cx + s * off, cy - s * 0.7), (cx + s * (off + 0.6), cy), (cx + s * off, cy + s * 0.7)]
            pygame.draw.lines(surf, c, False, pts, w)
    elif kind == "slow":     # jam
        pygame.draw.circle(surf, c, (cx, cy), int(s), max(2, w - 1))
        pygame.draw.line(surf, c, (cx, cy), (cx, cy - s * 0.62), w)
        pygame.draw.line(surf, c, (cx, cy), (cx + s * 0.45, cy + s * 0.1), w)
    elif kind == "fire":     # api
        outer = [(0, -1), (0.55, -0.1), (0.7, 0.35), (0.35, 0.85), (0, 1), (-0.35, 0.85),
                 (-0.7, 0.35), (-0.45, -0.05), (-0.2, -0.4)]
        pygame.draw.polygon(surf, c, [(cx + px * s, cy + py * s) for px, py in outer])
        inner = [(0, 0.1), (0.3, 0.5), (0.18, 0.85), (-0.18, 0.85), (-0.3, 0.5)]
        pygame.draw.polygon(surf, (255, 200, 80), [(cx + px * s, cy + py * s) for px, py in inner])
    elif kind == "laser":    # dua sinar ke atas
        for sx in (-0.5, 0.5):
            x = cx + s * sx
            pygame.draw.line(surf, c, (x, cy + s * 0.6), (x, cy - s * 0.35), w)
            pygame.draw.polygon(surf, c, [(x, cy - s), (x - s * 0.28, cy - s * 0.35), (x + s * 0.28, cy - s * 0.35)])
        pygame.draw.line(surf, c, (cx - s * 0.85, cy + s * 0.85), (cx + s * 0.85, cy + s * 0.85), w)
    elif kind == "life":     # hati
        draw_heart(surf, int(cx), int(cy - s * 0.4), max(3, int(s * 0.55)), c)


def draw_orb(surf, kind, cx, cy, tick, r=18, s=10, sparkle=True):
    """Orb power-up bergaya elemen: cincin berwarna + ikon + titik yang mengorbit."""
    _, col, _, _ = POWERUPS[kind]
    pulse = 1 + 0.07 * math.sin(tick * 0.15) if sparkle else 1
    rr = int(r * pulse)
    if sparkle:
        glow(surf, (cx, cy), r * 2, col, 85)
    pygame.draw.circle(surf, tuple(int(v * 0.3) for v in col), (cx, cy), rr)
    pygame.draw.circle(surf, col, (cx, cy), rr, 3)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), rr + 1, 1)
    draw_icon(surf, kind, cx, cy, s)
    if sparkle:
        for i in range(5):
            a = tick * 0.06 + i * math.tau / 5
            pygame.draw.circle(surf, col, (int(cx + math.cos(a) * (rr + 8)),
                                           int(cy + math.sin(a) * (rr + 8))), 2)


# ---------- Latar bergaya Inazuma ----------
def make_sky():
    stops = [(0.00, (16, 8, 40)), (0.45, (58, 24, 100)), (0.74, (150, 60, 150)),
             (0.80, (200, 100, 175)), (0.83, (60, 24, 90)), (1.00, (22, 10, 40))]
    surf = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                k = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0])
                c = lerp_color(stops[i][1], stops[i + 1][1], k)
                break
        pygame.draw.line(surf, c, (0, y), (WIDTH, y))
    return surf


def make_clouds():
    rng = random.Random(3)
    sw, sh = WIDTH // 4, HEIGHT // 4
    small = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for _ in range(30):
        x, y = rng.uniform(0, WIDTH), rng.uniform(0, 330)
        w, h = rng.uniform(220, 460), rng.uniform(50, 120)
        if y > 220:
            col = (110, 55, 160, rng.randint(55, 90))     # tepi awan terkena cahaya
        else:
            col = (rng.randint(24, 50), rng.randint(8, 24), rng.randint(55, 95), rng.randint(70, 120))
        for dx in (-sw, 0, sw):
            r = pygame.Rect(0, 0, w / 4, h / 4)
            r.center = (x / 4 + dx, y / 4)
            pygame.draw.ellipse(small, col, r)
    return pygame.transform.smoothscale(small, (WIDTH, HEIGHT))


def make_sigil_outer():
    S = 460
    c = S // 2
    surf = pygame.Surface((S, S), pygame.SRCALPHA)
    col = (*ELECTRO, 60)
    for rad, wd in ((222, 2), (209, 1), (160, 2), (120, 1)):
        pygame.draw.circle(surf, col, (c, c), rad, wd)
    for i in range(72):
        a = math.radians(i * 5)
        r2 = 220 if i % 6 == 0 else 214
        pygame.draw.line(surf, col, (c + math.cos(a) * 209, c + math.sin(a) * 209),
                         (c + math.cos(a) * r2, c + math.sin(a) * r2), 1)
    pts = [(c + math.cos(math.radians(k * 45)) * 190, c + math.sin(math.radians(k * 45)) * 190) for k in range(8)]
    for i in range(8):
        pygame.draw.line(surf, col, pts[i], pts[(i + 3) % 8], 1)
    return surf


def make_sigil_inner():
    S = 300
    c = S // 2
    surf = pygame.Surface((S, S), pygame.SRCALPHA)
    col = (*ELECTRO, 70)
    pygame.draw.circle(surf, col, (c, c), 140, 2)
    pygame.draw.circle(surf, col, (c, c), 40, 1)
    for off in (0, 60):
        pts = [(c + math.cos(math.radians(off + 90 + k * 120)) * 128,
                c + math.sin(math.radians(off + 90 + k * 120)) * 128) for k in range(3)]
        pygame.draw.polygon(surf, col, pts, 1)
    return surf


def make_front():
    """Siluet depan: laut, pulau, kuil, torii, dan pohon sakura (digambar sekali)."""
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dark = (24, 10, 40, 255)
    mid = (40, 18, 66, 255)
    rng = random.Random(7)

    # laut
    pygame.draw.rect(s, (26, 12, 48, 255), (0, 505, WIDTH, HEIGHT - 505))
    for y in range(512, HEIGHT, 13):
        for x in range(-20, WIDTH, 70):
            xo = x + (y % 26) * 2
            pygame.draw.line(s, (130, 80, 190, 45), (xo, y), (xo + 34, y), 1)

    # pulau
    pygame.draw.polygon(s, mid, [(430, 506), (480, 478), (540, 470), (600, 466), (660, 472),
                                 (720, 486), (790, 482), (800, 486), (800, 506)])
    pygame.draw.polygon(s, mid, [(0, 506), (0, 486), (60, 480), (120, 488), (200, 500), (215, 506)])

    # kuil bertingkat
    cx, base = 610, 468
    for i, w in enumerate((96, 76, 58, 40)):
        yb = base - i * 20
        pygame.draw.rect(s, dark, (cx - w // 2 + 6, yb - 14, w - 12, 14))
        pygame.draw.rect(s, (255, 190, 110, 255), (cx - 3, yb - 10, 6, 6))
        yt = yb - 14
        pygame.draw.polygon(s, dark, [(cx - w // 2 - 18, yt - 5), (cx - w // 2 - 8, yt + 2),
                                      (cx + w // 2 + 8, yt + 2), (cx + w // 2 + 18, yt - 5),
                                      (cx + w // 2, yt - 10), (cx - w // 2, yt - 10)])
    pygame.draw.line(s, dark, (cx, base - 4 * 20 + 6), (cx, base - 4 * 20 - 18), 3)

    # torii
    tx, y0 = 170, 392
    tor = (62, 14, 52, 255)
    pygame.draw.rect(s, tor, (tx - 36, y0, 9, 110))
    pygame.draw.rect(s, tor, (tx + 27, y0, 9, 110))
    pygame.draw.rect(s, tor, (tx - 44, y0 + 26, 88, 7))
    pygame.draw.polygon(s, tor, [(tx - 66, y0 + 2), (tx - 54, y0 - 9), (tx + 54, y0 - 9),
                                 (tx + 66, y0 + 2), (tx + 52, y0 + 9), (tx - 52, y0 + 9)])

    # pohon sakura di tepi
    pinks = [(255, 170, 205), (250, 140, 190), (255, 200, 225), (240, 120, 175)]

    def tree(x, by, sc):
        pygame.draw.polygon(s, (30, 14, 36, 255), [(x - 9 * sc, by), (x + 9 * sc, by),
                                                    (x + 4 * sc, by - 110 * sc), (x - 3 * sc, by - 125 * sc)])
        for ang in (-0.9, 0.7):
            pygame.draw.line(s, (30, 14, 36, 255), (x, by - 85 * sc),
                             (x + math.sin(ang) * 70 * sc, by - 85 * sc - math.cos(ang) * 55 * sc), int(5 * sc))
        ccx, ccy = x, by - 135 * sc
        for _ in range(55):
            a = rng.uniform(0, math.tau)
            rad = rng.random() ** 0.6 * 80 * sc
            px, py = ccx + math.cos(a) * rad * 1.3, ccy + math.sin(a) * rad * 0.8
            pygame.draw.circle(s, (*rng.choice(pinks), 215), (int(px), int(py)), int(rng.uniform(9, 20) * sc))

    tree(22, 602, 1.35)
    tree(790, 602, 1.2)
    return s


def make_bolt(x0, y0, x1, y1):
    pts = [(x0, y0), (x1, y1)]
    off = 70
    for _ in range(5):
        new = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            mx = (ax + bx) / 2 + random.uniform(-off, off) * 0.5
            my = (ay + by) / 2 + random.uniform(-off, off) * 0.3
            new += [(ax, ay), (mx, my)]
        new.append(pts[-1])
        pts = new
        off *= 0.6
    return pts


def draw_petal(surf, x, y, sz, ang, col):
    base = [(0, -sz), (sz * 0.6, 0), (0, sz * 0.5), (-sz * 0.6, 0)]
    ca, sa = math.cos(ang), math.sin(ang)
    pygame.draw.polygon(surf, col, [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in base])


# ---------- Objek game ----------
class Brick:
    def __init__(self, rect, color, tough):
        self.rect = rect
        self.color = color
        self.hp = 2 if tough else 1
        self.tough = tough

    def draw(self, surf):
        c = self.color
        if self.tough and self.hp == 1:
            c = tuple(int(v * 0.55) for v in c)
        pygame.draw.rect(surf, c, self.rect, border_radius=6)
        shine = pygame.Rect(self.rect.x + 3, self.rect.y + 3, self.rect.w - 6, self.rect.h // 3)
        light = tuple(min(255, v + 70) for v in c)
        pygame.draw.rect(surf, light, shine, border_radius=4)
        if self.tough:
            pygame.draw.rect(surf, (255, 255, 255), self.rect, 2, border_radius=6)
            if self.hp == 1:
                r = self.rect
                pygame.draw.lines(surf, (30, 20, 50), False, [
                    (r.x + r.w * 0.3, r.y + 2), (r.x + r.w * 0.45, r.centery),
                    (r.x + r.w * 0.35, r.bottom - 2)], 2)


class Ball:
    def __init__(self, x, y, vx=0.0, vy=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.trail = []


def build_bricks():
    bricks = []
    bw = (WIDTH - GAP * (COLS + 1)) // COLS
    for r in range(ROWS):
        for c in range(COLS):
            rect = pygame.Rect(GAP + c * (bw + GAP), TOP + r * (BRICK_H + GAP), bw, BRICK_H)
            bricks.append(Brick(rect, ROW_COLORS[r % len(ROW_COLORS)], random.random() < TOUGH_CHANCE))
    return bricks


def pick_powerup():
    kinds = list(POWERUPS)
    weights = [POWERUPS[k][3] for k in kinds]
    return random.choices(kinds, weights)[0]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Brick Breaker Inazuma")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 22, bold=True)
    big = pygame.font.SysFont("arial", 56, bold=True)
    small = pygame.font.SysFont("arial", 18, bold=True)
    

    canvas = pygame.Surface((WIDTH, HEIGHT))

    # ----- aset latar (dibuat sekali) -----
    sky = make_sky()
    clouds = make_clouds()
    sigil_outer = make_sigil_outer()
    sigil_inner = make_sigil_inner()
    front = make_front()
    flash_surf = pygame.Surface((WIDTH, HEIGHT))
    flash_surf.fill((190, 150, 255))
    slow_tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    slow_tint.fill((60, 255, 200, 22))
    mote_sprite = pygame.Surface((20, 20), pygame.SRCALPHA)
    for r in range(10, 0, -1):
        pygame.draw.circle(mote_sprite, (*ELECTRO, int(255 * (1 - r / 10) ** 2)), (10, 10), r)
    pygame.draw.circle(mote_sprite, (255, 235, 255, 255), (10, 10), 2)

    petal_cols = [(255, 175, 210), (250, 150, 195), (255, 205, 228)]
    petals = [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT), random.uniform(0.6, 1.6),
               random.uniform(0, 6.28), random.uniform(3, 6), random.uniform(0, 6.28),
               random.uniform(-0.05, 0.05), random.choice(petal_cols)] for _ in range(42)]
    motes = [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT), random.uniform(0.25, 0.8),
              random.uniform(0, 6.28)] for _ in range(32)]

    bolt_pts, bolt_branch = [], []
    bolt_life, bolt_timer, flash = 0, 120, 0.0

    # ----- state permainan -----
    paddle = pygame.Rect(0, HEIGHT - 45, PADDLE_W, PADDLE_H)
    paddle.centerx = WIDTH // 2
    paddle_w = float(PADDLE_W)
    paddle_hist = []
    balls = []
    speed = BASE_SPEED
    particles = []   # [x, y, vx, vy, life, maxlife, color, size, gravity]
    popups = []      # [x, y, text, life, color]
    rings = []       # [x, y, r, life, maxlife, color]
    drops = []       # [x, y, kind]
    bullets = []     # [x, y]
    effects = {}
    bricks = build_bricks()
    score, lives, level, combo = 0, 3, 1, 0
    shake = 0.0
    hue = 0.0
    laser_cd = 0
    tick = 0
    state = "ready"  # ready | playing | lost

    def reset_ball():
        balls.clear()
        balls.append(Ball(paddle.centerx, paddle.top - BALL_R - 1))

    def clear_extras():
        effects.clear()
        drops.clear()
        bullets.clear()

    def target_speed():
        s = min(MAX_SPEED, speed)
        return s * 0.65 if "slow" in effects else s

    def launch_ball():
        a = math.radians(random.uniform(250, 290))
        s = target_speed()
        balls[0].vx, balls[0].vy = s * math.cos(a), s * math.sin(a)

    def burst(x, y, color, n=16, grav=0.15):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(1.5, 6)
            particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp,
                              random.randint(20, 40), 40, color, random.uniform(2, 5), grav])

    def ring(x, y, color, maxr=70):
        rings.append([x, y, 10, 22, 22, color, maxr])

    def destroy_brick(b):
        nonlocal score, combo, speed, shake
        if b in bricks:
            bricks.remove(b)
        combo += 1
        pts = 10 * combo
        score += pts
        burst(b.rect.centerx, b.rect.centery, b.color)
        popups.append([b.rect.centerx, b.rect.centery, f"+{pts}", 40, b.color])
        shake = max(shake, 6)
        speed = min(MAX_SPEED, speed + 0.08)
        if random.random() < DROP_CHANCE:
            drops.append([float(b.rect.centerx), float(b.rect.centery), pick_powerup()])

    def apply_powerup(kind):
        nonlocal lives
        name, color, dur, _ = POWERUPS[kind]
        popups.append([paddle.centerx, paddle.top - 24, name, 50, color])
        ring(paddle.centerx, paddle.centery, color, 90)
        burst(paddle.centerx, paddle.top, color, 18, 0.05)
        if kind == "multi":
            extra = []
            for b in balls:
                for ang in (-0.45, 0.45):
                    c, s = math.cos(ang), math.sin(ang)
                    extra.append(Ball(b.x, b.y, b.vx * c - b.vy * s, b.vx * s + b.vy * c))
                ring(b.x, b.y, color, 50)
                burst(b.x, b.y, color, 12, 0.0)
            for e in extra:
                if len(balls) < MAX_BALLS:
                    balls.append(e)
        elif kind == "life":
            lives = min(5, lives + 1)
        else:
            effects[kind] = dur

    running = True
    reset_ball()
    while running:
        clock.tick(FPS)
        tick += 1
        hue += 1.2
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                if e.key == pygame.K_SPACE:
                    if state == "ready":
                        launch_ball()
                        state = "playing"
                    elif state == "lost":
                        bricks = build_bricks()
                        score, lives, level, combo = 0, 3, 1, 0
                        speed = BASE_SPEED
                        particles.clear()
                        popups.clear()
                        rings.clear()
                        clear_extras()
                        reset_ball()
                        state = "ready"

        # ----- Input: tombol panah -----
        keys = pygame.key.get_pressed()
        pspeed = PADDLE_SPEED * (1.7 if "fast" in effects else 1.0)
        if keys[pygame.K_LEFT]:
            paddle.x -= pspeed
        if keys[pygame.K_RIGHT]:
            paddle.x += pspeed

        paddle_w += ((PADDLE_W * 1.5 if "wide" in effects else PADDLE_W) - paddle_w) * 0.15
        cx = paddle.centerx
        paddle.w = int(paddle_w)
        paddle.centerx = cx
        paddle.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
        paddle_hist.append(paddle.copy())
        if len(paddle_hist) > 7:
            paddle_hist.pop(0)

        for k in list(effects):
            effects[k] -= 1
            if effects[k] <= 0:
                del effects[k]

        # ----- Update -----
        if state == "ready":
            balls[0].x, balls[0].y = paddle.centerx, paddle.top - BALL_R - 1
            balls[0].trail.clear()
        elif state == "playing":
            tgt = target_speed()
            fire = "fire" in effects

            for ball in balls[:]:
                m = math.hypot(ball.vx, ball.vy)
                if m:
                    ball.vx, ball.vy = ball.vx / m * tgt, ball.vy / m * tgt
                ball.x += ball.vx
                ball.y += ball.vy
                ball.trail.append((ball.x, ball.y))
                if len(ball.trail) > 14:
                    ball.trail.pop(0)

                if ball.x - BALL_R <= 0:
                    ball.x, ball.vx = BALL_R, abs(ball.vx)
                elif ball.x + BALL_R >= WIDTH:
                    ball.x, ball.vx = WIDTH - BALL_R, -abs(ball.vx)
                if ball.y - BALL_R <= 0:
                    ball.y, ball.vy = BALL_R, abs(ball.vy)

                rect = pygame.Rect(ball.x - BALL_R, ball.y - BALL_R, BALL_R * 2, BALL_R * 2)

                if rect.colliderect(paddle) and ball.vy > 0:
                    off = max(-1, min(1, (ball.x - paddle.centerx) / (paddle.w / 2)))
                    a = math.radians(270 + off * 60)
                    ball.vx, ball.vy = tgt * math.cos(a), tgt * math.sin(a)
                    ball.y = paddle.top - BALL_R
                    combo = 0
                    burst(ball.x, paddle.top, PADDLE_COLOR, 6)

                if fire:
                    for b in bricks[:]:
                        if rect.colliderect(b.rect):
                            shake = max(shake, 3)
                            destroy_brick(b)
                else:
                    for b in bricks:
                        if rect.colliderect(b.rect):
                            ox = min(rect.right - b.rect.left, b.rect.right - rect.left)
                            oy = min(rect.bottom - b.rect.top, b.rect.bottom - rect.top)
                            if ox < oy:
                                ball.vx *= -1
                            else:
                                ball.vy *= -1
                            b.hp -= 1
                            shake = max(shake, 3)
                            if b.hp <= 0:
                                destroy_brick(b)
                            else:
                                burst(b.rect.centerx, b.rect.centery, (255, 255, 255), 6)
                            break

                if ball.y - BALL_R > HEIGHT:
                    balls.remove(ball)

            if not balls:
                lives -= 1
                combo = 0
                shake = 12
                burst(paddle.centerx, HEIGHT - 10, (255, 80, 80), 30)
                clear_extras()
                reset_ball()
                state = "lost" if lives <= 0 else "ready"

            if state == "playing" and "laser" in effects:
                laser_cd -= 1
                if laser_cd <= 0:
                    for lx in (paddle.left + 8, paddle.right - 8):
                        bullets.append([lx, paddle.top])
                        burst(lx, paddle.top - 6, (255, 120, 120), 4, 0.0)
                    laser_cd = 20

            for bl in bullets[:]:
                bl[1] -= 12
                brect = pygame.Rect(bl[0] - 2, bl[1], 4, 14)
                hit = False
                for b in bricks:
                    if brect.colliderect(b.rect):
                        b.hp -= 1
                        hit = True
                        if b.hp <= 0:
                            destroy_brick(b)
                        else:
                            burst(b.rect.centerx, b.rect.centery, (255, 255, 255), 5)
                        break
                if hit or bl[1] < -20:
                    bullets.remove(bl)

            for d in drops[:]:
                d[1] += 2.6
                drect = pygame.Rect(d[0] - 20, d[1] - 20, 40, 40)
                if drect.colliderect(paddle):
                    apply_powerup(d[2])
                    drops.remove(d)
                elif d[1] > HEIGHT + 30:
                    drops.remove(d)

            if not bricks and state == "playing":
                level += 1
                speed = min(MAX_SPEED, BASE_SPEED + 0.6 * (level - 1))
                bricks = build_bricks()
                clear_extras()
                reset_ball()
                state = "ready"
                popups.append([WIDTH // 2, HEIGHT // 2, f"LEVEL {level}!", 70, (255, 255, 120)])

            # api: bola dan papan menyemburkan api
            if "fire" in effects:
                for ball in balls:
                    particles.append([ball.x + random.uniform(-4, 4), ball.y + random.uniform(-2, 6),
                                      random.uniform(-0.6, 0.6), random.uniform(-2.2, -0.8),
                                      random.randint(14, 22), 22,
                                      random.choice([(255, 140, 40), (255, 200, 70), (255, 90, 30)]),
                                      random.uniform(2.5, 4.5), -0.04])
                particles.append([random.uniform(paddle.left, paddle.right), paddle.top,
                                  random.uniform(-0.3, 0.3), random.uniform(-2.0, -0.8),
                                  random.randint(14, 22), 22, (255, 150, 50), random.uniform(2, 4), -0.04])

        # ----- Latar dinamis -----
        bolt_timer -= 1
        if bolt_timer <= 0:
            x0 = random.uniform(100, 700)
            x1, y1 = x0 + random.uniform(-120, 120), random.uniform(420, 470)
            bolt_pts = make_bolt(x0, -10, x1, y1)
            mid = bolt_pts[len(bolt_pts) // 2]
            bolt_branch = make_bolt(mid[0], mid[1], mid[0] + random.uniform(-140, 140), mid[1] + 150)
            bolt_life, flash = 10, 70.0
            bolt_timer = random.randint(150, 420)
        if bolt_life > 0:
            bolt_life -= 1
        flash *= 0.8

        for p in petals:
            p[0] += 0.5 + math.sin(p[3]) * 0.6
            p[1] += p[2]
            p[3] += 0.03
            p[5] += p[6]
            if p[1] > HEIGHT + 10 or p[0] > WIDTH + 10:
                p[0], p[1] = random.uniform(-100, WIDTH), -10
        for m_ in motes:
            m_[1] -= m_[2]
            m_[3] += 0.05
            if m_[1] < -10:
                m_[0], m_[1] = random.uniform(0, WIDTH), HEIGHT + 10

        # partikel, cincin, popup
        for p in particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += p[8]
            p[4] -= 1
        particles[:] = [p for p in particles if p[4] > 0]
        for rg in rings:
            rg[2] += (rg[6] - rg[2]) * 0.18
            rg[3] -= 1
        rings[:] = [rg for rg in rings if rg[3] > 0]
        for t in popups:
            t[1] -= 0.8
            t[3] -= 1
        popups[:] = [t for t in popups if t[3] > 0]
        shake *= 0.85

        # ================= GAMBAR =================
        canvas.blit(sky, (0, 0))
        off = (tick * 0.25) % WIDTH
        canvas.blit(clouds, (-off, 0))
        canvas.blit(clouds, (WIDTH - off, 0))

        if bolt_life > 0:
            k = bolt_life / 10
            for pts, wd in ((bolt_pts, 1), (bolt_branch, 0)):
                glow_col = tuple(int(v * k) for v in (170, 110, 255))
                pygame.draw.lines(canvas, glow_col, False, pts, 8 - wd * 3)
                pygame.draw.lines(canvas, (255, 255, 255), False, pts, 3 - wd)

        for img, ang, cy_ in ((sigil_outer, tick * 0.15, 330), (sigil_inner, -tick * 0.3, 330)):
            rot = pygame.transform.rotate(img, ang)
            canvas.blit(rot, rot.get_rect(center=(WIDTH // 2, cy_)))

        canvas.blit(front, (0, 0))

        if flash > 2:
            flash_surf.set_alpha(int(flash))
            canvas.blit(flash_surf, (0, 0))

        for p in petals:
            draw_petal(canvas, p[0], p[1], p[4], p[5], p[7])
        for m_ in motes:
            mote_sprite.set_alpha(int(110 + 110 * math.sin(m_[3])))
            canvas.blit(mote_sprite, (m_[0] - 10 + math.sin(m_[3] * 0.7) * 6, m_[1] - 10))

        # ----- objek game -----
        for b in bricks:
            b.draw(canvas)

        fire = "fire" in effects

        # bayangan papan saat CEPAT
        if "fast" in effects:
            for idx, alpha in ((0, 35), (2, 60), (4, 90)):
                if idx < len(paddle_hist):
                    gr = paddle_hist[idx]
                    gs = pygame.Surface((gr.w, gr.h), pygame.SRCALPHA)
                    pygame.draw.rect(gs, (*PADDLE_COLOR, alpha), gs.get_rect(), border_radius=8)
                    canvas.blit(gs, gr.topleft)

        # jejak & bola
        for ball in balls:
            n = len(ball.trail)
            for i, (tx, ty) in enumerate(ball.trail):
                kk = (i + 1) / n
                col = (255, int(120 + 100 * kk), 40) if fire else hue_color(hue - (n - i) * 8)
                pygame.draw.circle(canvas, col, (int(tx), int(ty)), max(1, int(BALL_R * kk * 0.8)))
        for ball in balls:
            bpos = (int(ball.x), int(ball.y))
            glow(canvas, bpos, 26, (255, 150, 50) if fire else (255, 255, 255), 80)
            pygame.draw.circle(canvas, (255, 200, 90) if fire else (255, 255, 255), bpos, BALL_R)
            if "slow" in effects:   # riak air hijau di sekeliling bola
                for kk in (0, 20):
                    rr = 12 + ((tick * 0.6 + kk) % 40)
                    fade = 1 - (rr - 12) / 40
                    pygame.draw.circle(canvas, tuple(int(v * fade) for v in (80, 230, 160)), bpos, int(rr), 2)

        # papan
        pc = (255, 160, 70) if fire else PADDLE_COLOR
        soft_rect_glow(canvas, paddle, pc)
        pygame.draw.rect(canvas, pc, paddle, border_radius=8)
        pygame.draw.rect(canvas, (255, 255, 255),
                         (paddle.x + 8, paddle.y + 3, paddle.w - 16, 3), border_radius=2)
        if "wide" in effects:       # panah berdenyut di kedua ujung
            pulse = math.sin(tick * 0.2) * 3
            my = paddle.centery
            pygame.draw.polygon(canvas, (180, 235, 255), [(paddle.left - 6 - pulse, my),
                                (paddle.left - 16 - pulse, my - 7), (paddle.left - 16 - pulse, my + 7)])
            pygame.draw.polygon(canvas, (180, 235, 255), [(paddle.right + 6 + pulse, my),
                                (paddle.right + 16 + pulse, my - 7), (paddle.right + 16 + pulse, my + 7)])
        if "laser" in effects:
            for lx in (paddle.left + 4, paddle.right - 12):
                pygame.draw.rect(canvas, (255, 70, 70), (lx, paddle.top - 7, 8, 9), border_radius=2)

        for bl in bullets:
            glow(canvas, (int(bl[0]), int(bl[1]) + 7), 12, (255, 80, 80), 100)
            pygame.draw.rect(canvas, (255, 150, 150), (bl[0] - 2, bl[1], 4, 14), border_radius=2)

        for d in drops:
            draw_orb(canvas, d[2], int(d[0]), int(d[1]), tick)

        for p in particles:
            a = p[4] / p[5]
            pygame.draw.circle(canvas, tuple(int(c * a) for c in p[6]),
                               (int(p[0]), int(p[1])), max(1, int(p[7] * a)))
        for rg in rings:
            a = rg[3] / rg[4]
            pygame.draw.circle(canvas, tuple(int(c * a) for c in rg[5]),
                               (int(rg[0]), int(rg[1])), int(rg[2]), 3)
        for t in popups:
            text_center(canvas, font, t[2], (t[0], t[1]), t[4])

        if "slow" in effects:
            canvas.blit(slow_tint, (0, 0))

        # ----- HUD -----
        canvas.blit(font.render(f"Skor: {score}", True, (255, 255, 255)), (14, 12))
        text_center(canvas, font, f"Level {level}", (WIDTH // 2, 24), (255, 230, 120))
        for i in range(lives):
            draw_heart(canvas, WIDTH - 30 - i * 34, 22, 9, (255, 80, 110))
        if combo >= 2:
            text_center(canvas, small, f"COMBO x{combo}", (WIDTH // 2, 50), hue_color(hue * 2))
        for i, (k, left) in enumerate(effects.items()):
            _, col, dur, _ = POWERUPS[k]
            y = 52 + i * 26
            draw_orb(canvas, k, 25, y, tick, r=10, s=6, sparkle=False)
            pygame.draw.rect(canvas, (50, 40, 80), (44, y - 3, 90, 7), border_radius=3)
            pygame.draw.rect(canvas, col, (44, y - 3, int(90 * left / dur), 7), border_radius=3)

        if state == "ready":
            text_center(canvas, font, "Tekan SPASI untuk meluncurkan bola   |   ← → untuk bergerak",
                        (WIDTH // 2, HEIGHT // 2 + 80))
        elif state == "lost":
            text_center(canvas, big, "GAME OVER", (WIDTH // 2, HEIGHT // 2 - 10), (255, 100, 120))
            text_center(canvas, font, f"Skor akhir: {score}  -  SPASI untuk main lagi",
                        (WIDTH // 2, HEIGHT // 2 + 45))

        ox = random.uniform(-shake, shake) if shake > 0.5 else 0
        oy = random.uniform(-shake, shake) if shake > 0.5 else 0
        screen.fill((0, 0, 0))
        screen.blit(canvas, (ox, oy))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()