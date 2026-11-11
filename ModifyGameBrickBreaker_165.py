import math
import os
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
MAX_LIVES = 5

ROWS, COLS = 6, 10
GAP = 5
TOP = 112             # ruang untuk HUD di atas
BRICK_H = 24
TOTAL_BRICKS = ROWS * COLS
TOUGH_CHANCE = 0.25   # brick yang butuh 2 pukulan
DROP_CHANCE = 0.20    # peluang brick pecah menjatuhkan power-up

PADDLE_COLOR = (130, 205, 255)
ELECTRO = (200, 140, 255)
LABEL_COLOR = (175, 155, 215)
GOLD = (255, 214, 100)

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
POWERUP_DESC = {
    "multi": "Bola membelah jadi tiga",
    "wide":  "Papan jadi lebih lebar",
    "fast":  "Papan bergerak lebih cepat",
    "slow":  "Bola melambat sementara",
    "fire":  "Bola menembus semua brick",
    "laser": "Papan menembak otomatis",
    "life":  "Tambah 1 nyawa",
}
LEGEND_ORDER = ["multi", "wide", "fast", "slow", "fire", "laser", "life"]

BEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_score.txt")


# ---------- Skor terbaik ----------
def load_best():
    try:
        with open(BEST_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_best(v):
    try:
        with open(BEST_FILE, "w") as f:
            f.write(str(int(v)))
    except OSError:
        pass


def fmt_num(n):
    return f"{int(n):,}".replace(",", ".")


def fmt_time(frames):
    s = frames // FPS
    return f"{s // 60:02d}:{s % 60:02d}"


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


def draw_text(surf, font, text, pos, color=(255, 255, 255), anchor="topleft", alpha=None):
    img = font.render(text, True, color)
    if alpha is not None:
        img.set_alpha(alpha)
    r = img.get_rect(**{anchor: pos})
    surf.blit(img, r)
    return r


def blit_scaled(surf, img, topleft, scale):
    if scale > 1.01:
        w, h = img.get_size()
        img2 = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        surf.blit(img2, (topleft[0], topleft[1] - (img2.get_height() - h) // 2))
    else:
        surf.blit(img, topleft)


# ---------- Komponen UI ----------
_panel_cache = {}


def panel(surf, rect, fill=(16, 9, 36, 150), border=(200, 140, 255, 90), radius=14):
    key = (rect.w, rect.h, fill, border, radius)
    p = _panel_cache.get(key)
    if p is None:
        p = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(p, fill, p.get_rect(), border_radius=radius)
        pygame.draw.rect(p, border, p.get_rect(), 1, border_radius=radius)
        _panel_cache[key] = p
    surf.blit(p, rect.topleft)


def bar(surf, rect, frac, color, bg=(50, 40, 80)):
    pygame.draw.rect(surf, bg, rect, border_radius=rect.h // 2)
    w = int(rect.w * max(0.0, min(1.0, frac)))
    if w > 0:
        pygame.draw.rect(surf, color, (rect.x, rect.y, max(w, rect.h), rect.h), border_radius=rect.h // 2)


# ---------- Ikon skill ----------
def draw_icon(surf, kind, cx, cy, s, c=(255, 255, 255)):
    w = max(2, int(s * 0.28))
    if kind == "multi":
        pygame.draw.line(surf, c, (cx, cy - s * 0.1), (cx - s * 0.75, cy + s * 0.5), 1)
        pygame.draw.line(surf, c, (cx, cy - s * 0.1), (cx + s * 0.75, cy + s * 0.5), 1)
        pygame.draw.circle(surf, c, (cx, int(cy - s * 0.25)), max(2, int(s * 0.36)))
        pygame.draw.circle(surf, c, (int(cx - s * 0.75), int(cy + s * 0.55)), max(2, int(s * 0.28)))
        pygame.draw.circle(surf, c, (int(cx + s * 0.75), int(cy + s * 0.55)), max(2, int(s * 0.28)))
    elif kind == "wide":
        pygame.draw.line(surf, c, (cx - s * 0.8, cy), (cx + s * 0.8, cy), w)
        pygame.draw.polygon(surf, c, [(cx - s, cy), (cx - s * 0.45, cy - s * 0.5), (cx - s * 0.45, cy + s * 0.5)])
        pygame.draw.polygon(surf, c, [(cx + s, cy), (cx + s * 0.45, cy - s * 0.5), (cx + s * 0.45, cy + s * 0.5)])
    elif kind == "fast":
        for off in (-0.55, 0.1):
            pts = [(cx + s * off, cy - s * 0.7), (cx + s * (off + 0.6), cy), (cx + s * off, cy + s * 0.7)]
            pygame.draw.lines(surf, c, False, pts, w)
    elif kind == "slow":
        pygame.draw.circle(surf, c, (cx, cy), int(s), max(2, w - 1))
        pygame.draw.line(surf, c, (cx, cy), (cx, cy - s * 0.62), w)
        pygame.draw.line(surf, c, (cx, cy), (cx + s * 0.45, cy + s * 0.1), w)
    elif kind == "fire":
        outer = [(0, -1), (0.55, -0.1), (0.7, 0.35), (0.35, 0.85), (0, 1), (-0.35, 0.85),
                 (-0.7, 0.35), (-0.45, -0.05), (-0.2, -0.4)]
        pygame.draw.polygon(surf, c, [(cx + px * s, cy + py * s) for px, py in outer])
        inner = [(0, 0.1), (0.3, 0.5), (0.18, 0.85), (-0.18, 0.85), (-0.3, 0.5)]
        pygame.draw.polygon(surf, (255, 200, 80), [(cx + px * s, cy + py * s) for px, py in inner])
    elif kind == "laser":
        for sx in (-0.5, 0.5):
            x = cx + s * sx
            pygame.draw.line(surf, c, (x, cy + s * 0.6), (x, cy - s * 0.35), w)
            pygame.draw.polygon(surf, c, [(x, cy - s), (x - s * 0.28, cy - s * 0.35), (x + s * 0.28, cy - s * 0.35)])
        pygame.draw.line(surf, c, (cx - s * 0.85, cy + s * 0.85), (cx + s * 0.85, cy + s * 0.85), w)
    elif kind == "life":
        draw_heart(surf, int(cx), int(cy - s * 0.4), max(3, int(s * 0.55)), c)


def draw_orb(surf, kind, cx, cy, tick, r=18, s=10, sparkle=True):
    _, col, _, _ = POWERUPS[kind]
    pulse = 1 + 0.07 * math.sin(tick * 0.15) if sparkle else 1
    rr = int(r * pulse)
    if sparkle:
        glow(surf, (cx, cy), r * 2, col, 85)
    pygame.draw.circle(surf, tuple(int(v * 0.3) for v in col), (cx, cy), rr)
    pygame.draw.circle(surf, col, (cx, cy), rr, 3 if r > 12 else 2)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), rr + 1, 1)
    draw_icon(surf, kind, cx, cy, s)
    if sparkle:
        for i in range(5):
            a = tick * 0.06 + i * math.tau / 5
            pygame.draw.circle(surf, col, (int(cx + math.cos(a) * (rr + 8)),
                                           int(cy + math.sin(a) * (rr + 8))), 2)


# ---------- Latar bergaya badai petir ----------
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
            col = (110, 55, 160, rng.randint(55, 90))
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
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dark = (24, 10, 40, 255)
    mid = (40, 18, 66, 255)
    rng = random.Random(7)

    pygame.draw.rect(s, (26, 12, 48, 255), (0, 505, WIDTH, HEIGHT - 505))
    for y in range(512, HEIGHT, 13):
        for x in range(-20, WIDTH, 70):
            xo = x + (y % 26) * 2
            pygame.draw.line(s, (130, 80, 190, 45), (xo, y), (xo + 34, y), 1)

    pygame.draw.polygon(s, mid, [(430, 506), (480, 478), (540, 470), (600, 466), (660, 472),
                                 (720, 486), (790, 482), (800, 486), (800, 506)])
    pygame.draw.polygon(s, mid, [(0, 506), (0, 486), (60, 480), (120, 488), (200, 500), (215, 506)])

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

    tx, y0 = 170, 392
    tor = (62, 14, 52, 255)
    pygame.draw.rect(s, tor, (tx - 36, y0, 9, 110))
    pygame.draw.rect(s, tor, (tx + 27, y0, 9, 110))
    pygame.draw.rect(s, tor, (tx - 44, y0 + 26, 88, 7))
    pygame.draw.polygon(s, tor, [(tx - 66, y0 + 2), (tx - 54, y0 - 9), (tx + 54, y0 - 9),
                                 (tx + 66, y0 + 2), (tx + 52, y0 + 9), (tx - 52, y0 + 9)])

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


# ---------- Gambar HUD & layar ----------
def draw_hud(surf, fonts, score_img_scale, disp_score, best, level, bricks_left, play_frames,
             lives, combo, effects, tick, hue):
    f_label, f_text, f_val = fonts["label"], fonts["text"], fonts["val"]

    # Panel skor
    r = pygame.Rect(10, 8, 230, 58)
    panel(surf, r)
    draw_text(surf, f_label, "SKOR", (r.x + 16, r.y + 8), LABEL_COLOR)
    img = f_val.render(fmt_num(disp_score), True, (255, 255, 255))
    blit_scaled(surf, img, (r.x + 16, r.y + 22), score_img_scale)
    draw_text(surf, f_label, "TERBAIK", (r.right - 14, r.y + 10), LABEL_COLOR, "topright")
    draw_text(surf, f_text, fmt_num(best), (r.right - 14, r.y + 26), GOLD, "topright")

    # Panel level + progres
    r = pygame.Rect((WIDTH - 200) // 2, 8, 200, 58)
    panel(surf, r)
    pct = 1 - bricks_left / TOTAL_BRICKS
    draw_text(surf, f_text, f"LEVEL {level}", (r.x + 16, r.y + 10), (255, 235, 150))
    draw_text(surf, f_label, f"{int(pct * 100)}%", (r.right - 16, r.y + 13), LABEL_COLOR, "topright")
    bar(surf, pygame.Rect(r.x + 16, r.y + 36, r.w - 32, 9), pct, (120, 220, 255))
    draw_text(surf, f_label, f"{TOTAL_BRICKS - bricks_left}/{TOTAL_BRICKS} brick", (r.centerx, r.bottom - 4),
              LABEL_COLOR, "midbottom")

    # Panel waktu + nyawa
    r = pygame.Rect(WIDTH - 240, 8, 230, 58)
    panel(surf, r)
    draw_text(surf, f_label, "WAKTU", (r.x + 16, r.y + 8), LABEL_COLOR)
    draw_text(surf, f_val, fmt_time(play_frames), (r.x + 16, r.y + 22), (255, 255, 255))
    draw_text(surf, f_label, "NYAWA", (r.right - 14, r.y + 10), LABEL_COLOR, "topright")
    for i in range(MAX_LIVES):
        hx = r.right - 22 - (MAX_LIVES - 1 - i) * 19
        col = (255, 80, 110) if i < lives else (70, 48, 98)
        draw_heart(surf, hx, r.y + 34, 6, col)

    # Baris kedua: chip efek aktif (kiri) + combo (kanan)
    x = 10
    for kind, left in effects.items():
        name, col, dur, _ = POWERUPS[kind]
        cr = pygame.Rect(x, 74, 124, 28)
        panel(surf, cr, radius=12, border=(*col, 140))
        draw_orb(surf, kind, cr.x + 15, cr.centery, tick, r=10, s=6, sparkle=False)
        draw_text(surf, f_label, name, (cr.x + 32, cr.y + 3), col)
        draw_text(surf, f_label, f"{math.ceil(left / FPS)}d", (cr.right - 8, cr.y + 3), (255, 255, 255), "topright")
        bar(surf, pygame.Rect(cr.x + 32, cr.y + 19, cr.w - 42, 4), left / dur, col)
        x += cr.w + 6

    if combo >= 2:
        cr = pygame.Rect(WIDTH - 10 - 132, 74, 132, 28)
        panel(surf, cr, radius=12, border=(255, 200, 90, 170))
        text_center(surf, f_text, f"COMBO x{combo}", cr.center, hue_color(hue * 2))


def draw_dim(surf, dim):
    surf.blit(dim, (0, 0))


def draw_menu(surf, fonts, best, tick):
    f_label, f_text, f_title = fonts["label"], fonts["text"], fonts["title"]
    card = pygame.Rect(120, 50, 560, 500)
    panel(surf, card, fill=(14, 8, 34, 215), border=(200, 140, 255, 140), radius=22)
    text_center(surf, f_title, "BRICK BREAKER", (WIDTH // 2, card.y + 46), (255, 255, 255))
    text_center(surf, f_label, "EDISI BADAI PETIR", (WIDTH // 2, card.y + 82), ELECTRO)

    draw_text(surf, f_label, "POWER-UP", (card.x + 30, card.y + 112), LABEL_COLOR)
    pygame.draw.line(surf, (90, 70, 130), (card.x + 100, card.y + 119), (card.right - 30, card.y + 119), 1)
    for i, kind in enumerate(LEGEND_ORDER):
        col_i, row_i = (0, i) if i < 4 else (1, i - 4)
        x = card.x + 30 + col_i * 262
        y = card.y + 134 + row_i * 46
        draw_orb(surf, kind, x + 15, y + 17, tick, r=13, s=8, sparkle=False)
        draw_text(surf, f_text, POWERUPS[kind][0], (x + 40, y), POWERUPS[kind][1])
        draw_text(surf, f_label, POWERUP_DESC[kind], (x + 40, y + 20), (210, 195, 235))

    # info brick keras
    by = card.y + 330
    br = pygame.Rect(card.x + 30, by, 40, 16)
    pygame.draw.rect(surf, (255, 150, 60), br, border_radius=5)
    pygame.draw.rect(surf, (255, 255, 255), br, 2, border_radius=5)
    draw_text(surf, f_label, "Brick bertepi putih butuh 2 pukulan (jadi gelap & retak setelah pukulan pertama)",
              (br.right + 12, by + 1), (210, 195, 235))

    # kontrol
    ky = card.y + 372
    keys = [("← →", "Gerak"), ("SPASI", "Luncurkan"), ("P", "Jeda")]
    kx = card.x + 30
    for k, label in keys:
        kr = draw_text(surf, f_text, k, (kx + 10, ky + 4), (255, 255, 255))
        box = kr.inflate(20, 10)
        panel(surf, box, radius=8, fill=(60, 40, 100, 200), border=(200, 140, 255, 160))
        draw_text(surf, f_text, k, kr.topleft, (255, 255, 255))
        lr = draw_text(surf, f_label, label, (box.right + 8, ky + 8), LABEL_COLOR)
        kx = lr.right + 28

    draw_text(surf, f_label, "SKOR TERBAIK", (WIDTH // 2, card.y + 424), LABEL_COLOR, "midtop")
    text_center(surf, f_text, fmt_num(best), (WIDTH // 2, card.y + 454), GOLD)

    a = int(150 + 105 * math.sin(tick * 0.08))
    draw_text(surf, fonts["cta"], "Tekan SPASI untuk mulai", (WIDTH // 2, card.bottom - 20),
              (255, 255, 255), "center", alpha=a)


def draw_ready(surf, fonts, tick):
    r = pygame.Rect(0, 0, 380, 40)
    r.center = (WIDTH // 2, 410)
    panel(surf, r, radius=20)
    a = int(170 + 85 * math.sin(tick * 0.1))
    draw_text(surf, fonts["text"], "Tekan SPASI untuk meluncurkan bola", r.center, (255, 255, 255), "center", alpha=a)


def draw_pause(surf, fonts, dim):
    surf.blit(dim, (0, 0))
    r = pygame.Rect(0, 0, 320, 130)
    r.center = (WIDTH // 2, HEIGHT // 2)
    panel(surf, r, fill=(14, 8, 34, 225), border=(200, 140, 255, 150), radius=20)
    text_center(surf, fonts["title"], "JEDA", (r.centerx, r.y + 46), (255, 255, 255))
    text_center(surf, fonts["label"], "Tekan P untuk melanjutkan", (r.centerx, r.y + 96), LABEL_COLOR)


def draw_gameover(surf, fonts, dim, stats, tick):
    surf.blit(dim, (0, 0))
    f_label, f_text = fonts["label"], fonts["text"]
    card = pygame.Rect(0, 0, 430, 330)
    card.center = (WIDTH // 2, HEIGHT // 2)
    panel(surf, card, fill=(14, 8, 34, 230), border=(255, 100, 130, 160), radius=22)
    text_center(surf, fonts["title"], "GAME OVER", (card.centerx, card.y + 44), (255, 100, 120))
    if stats["new_record"]:
        a = int(170 + 85 * math.sin(tick * 0.12))
        draw_text(surf, f_text, "REKOR BARU!", (card.centerx, card.y + 84), GOLD, "center", alpha=a)
    items = [("SKOR", fmt_num(stats["score"])), ("TERBAIK", fmt_num(stats["best"])),
             ("WAKTU", fmt_time(stats["frames"])), ("LEVEL", str(stats["level"])),
             ("BRICK HANCUR", str(stats["bricks"])), ("COMBO MAKS", f"x{stats['max_combo']}")]
    for i, (label, value) in enumerate(items):
        cx_ = card.x + 40 + (i % 2) * 190
        cy_ = card.y + 112 + (i // 2) * 54
        draw_text(surf, f_label, label, (cx_, cy_), LABEL_COLOR)
        draw_text(surf, fonts["val"], value, (cx_, cy_ + 14), (255, 255, 255))
    a = int(150 + 105 * math.sin(tick * 0.08))
    draw_text(surf, fonts["cta"], "Tekan SPASI untuk main lagi", (card.centerx, card.bottom - 26),
              (255, 255, 255), "center", alpha=a)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Brick Breaker - Badai Petir")
    clock = pygame.time.Clock()

    fam = "segoeui,helveticaneue,arial"
    fonts = {
        "label": pygame.font.SysFont(fam, 12, bold=True),
        "text": pygame.font.SysFont(fam, 16, bold=True),
        "val": pygame.font.SysFont(fam, 28, bold=True),
        "cta": pygame.font.SysFont(fam, 20, bold=True),
        "title": pygame.font.SysFont(fam, 44, bold=True),
        "pop": pygame.font.SysFont(fam, 22, bold=True),
    }

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
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 20, 150))
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
    rings = []       # [x, y, r, life, maxlife, color, maxr]
    drops = []       # [x, y, kind]
    bullets = []     # [x, y]
    effects = {}
    bricks = build_bricks()
    score, lives, level, combo = 0, 3, 1, 0
    disp_score = 0.0
    score_pulse = 0.0
    play_frames = 0
    bricks_destroyed = 0
    max_combo = 0
    best = load_best()
    best_at_start = best
    new_record = False
    shake = 0.0
    hue = 0.0
    laser_cd = 0
    tick = 0
    paused = False
    state = "menu"   # menu | ready | playing | lost

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
        nonlocal score, combo, speed, shake, score_pulse, bricks_destroyed, max_combo
        if b in bricks:
            bricks.remove(b)
        combo += 1
        max_combo = max(max_combo, combo)
        bricks_destroyed += 1
        pts = 10 * combo
        score += pts
        score_pulse = 1.0
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
            lives = min(MAX_LIVES, lives + 1)
        else:
            effects[kind] = dur

    def new_game():
        nonlocal bricks, score, lives, level, combo, speed, disp_score, play_frames
        nonlocal bricks_destroyed, max_combo, best_at_start, new_record, state
        bricks = build_bricks()
        score, lives, level, combo = 0, 3, 1, 0
        disp_score = 0.0
        play_frames = 0
        bricks_destroyed = 0
        max_combo = 0
        best_at_start = best
        new_record = False
        speed = BASE_SPEED
        particles.clear()
        popups.clear()
        rings.clear()
        clear_extras()
        reset_ball()
        state = "ready"

    running = True
    reset_ball()
    while running:
        clock.tick(FPS)
        tick += 1
        hue += 1.2
        active = (not paused) and state != "menu"

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                if e.key == pygame.K_p and state in ("ready", "playing"):
                    paused = not paused
                if e.key == pygame.K_SPACE and not paused:
                    if state == "menu":
                        new_game()
                    elif state == "ready":
                        launch_ball()
                        state = "playing"
                    elif state == "lost":
                        new_game()

        if active:
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
                play_frames += 1
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
                    if lives <= 0:
                        state = "lost"
                        new_record = score > best_at_start and score > 0
                        if score > best:
                            best = score
                            save_best(best)
                    else:
                        state = "ready"

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

            # partikel, cincin, popup, skor
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
            disp_score += (score - disp_score) * 0.18
            if abs(score - disp_score) < 1:
                disp_score = score
            score_pulse *= 0.88

        # ----- Latar dinamis (selalu bergerak) -----
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

        if "fast" in effects:
            for idx, alpha in ((0, 35), (2, 60), (4, 90)):
                if idx < len(paddle_hist):
                    gr = paddle_hist[idx]
                    gs = pygame.Surface((gr.w, gr.h), pygame.SRCALPHA)
                    pygame.draw.rect(gs, (*PADDLE_COLOR, alpha), gs.get_rect(), border_radius=8)
                    canvas.blit(gs, gr.topleft)

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
            if "slow" in effects:
                for kk in (0, 20):
                    rr = 12 + ((tick * 0.6 + kk) % 40)
                    fade = 1 - (rr - 12) / 40
                    pygame.draw.circle(canvas, tuple(int(v * fade) for v in (80, 230, 160)), bpos, int(rr), 2)

        pc = (255, 160, 70) if fire else PADDLE_COLOR
        soft_rect_glow(canvas, paddle, pc)
        pygame.draw.rect(canvas, pc, paddle, border_radius=8)
        pygame.draw.rect(canvas, (255, 255, 255),
                         (paddle.x + 8, paddle.y + 3, paddle.w - 16, 3), border_radius=2)
        if "wide" in effects:
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
            text_center(canvas, fonts["pop"], t[2], (t[0], t[1]), t[4])

        if "slow" in effects:
            canvas.blit(slow_tint, (0, 0))

        # ----- HUD -----
        if state != "menu":
            draw_hud(canvas, fonts, 1 + 0.22 * score_pulse, disp_score, max(best, score), level,
                     len(bricks), play_frames, lives, combo, effects, tick, hue)
            if state in ("ready", "playing") and not paused:
                draw_text(canvas, fonts["label"], "←  →  Gerak        SPASI  Luncurkan        P  Jeda",
                          (WIDTH // 2, HEIGHT - 12), (190, 170, 230), "center", alpha=170)
        if state == "ready" and not paused:
            draw_ready(canvas, fonts, tick)

        # ----- Layar overlay -----
        if state == "menu":
            canvas.blit(dim, (0, 0))
            draw_menu(canvas, fonts, best, tick)
        elif state == "lost":
            draw_gameover(canvas, fonts, dim, {
                "score": score, "best": best, "frames": play_frames, "level": level,
                "bricks": bricks_destroyed, "max_combo": max_combo, "new_record": new_record}, tick)
        elif paused:
            draw_pause(canvas, fonts, dim)

        ox = random.uniform(-shake, shake) if shake > 0.5 else 0
        oy = random.uniform(-shake, shake) if shake > 0.5 else 0
        screen.fill((0, 0, 0))
        screen.blit(canvas, (ox, oy))
        pygame.display.flip()

    if score > best:
        save_best(score)
    pygame.quit()


if __name__ == "__main__":
    main()