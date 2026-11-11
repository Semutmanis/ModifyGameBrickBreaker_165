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

PADDLE_COLOR = (110, 200, 255)

ROW_COLORS = [
    (255, 85, 110), (255, 150, 60), (255, 220, 70),
    (80, 230, 140), (70, 190, 255), (180, 110, 255),
]

# nama, warna, durasi (frame), bobot kemunculan
POWERUPS = {
    "multi": ("x3",     (190, 120, 255), 0,   3),
    "wide":  ("LEBAR",  (80, 200, 255),  600, 3),
    "fast":  ("CEPAT",  (255, 220, 70),  600, 2),
    "slow":  ("LAMBAT", (80, 230, 140),  480, 2),
    "fire":  ("API",    (255, 120, 40),  420, 2),
    "laser": ("LASER",  (255, 70, 70),   480, 2),
    "life":  ("+1",     (255, 90, 120),  0,   1),
}


# ---------- Utilitas gambar ----------
def make_gradient():
    surf = pygame.Surface((WIDTH, HEIGHT))
    top, bottom = (14, 10, 40), (40, 14, 70)
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(surf, c, (0, y), (WIDTH, y))
    return surf


def glow(surf, pos, radius, color, alpha=70):
    g = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        a = int(alpha * (1 - r / radius) ** 1.5) + 3
        pygame.draw.circle(g, (*color, min(255, a)), (radius, radius), r)
    surf.blit(g, (pos[0] - radius, pos[1] - radius))


def soft_rect_glow(surf, rect, color, spread=12, alpha=55):
    """Cahaya tipis berbentuk papan (bukan lingkaran)."""
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
            c = tuple(int(v * 0.55) for v in c)  # gelap = sudah retak
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
    pygame.display.set_caption("Brick Breaker Power-Up")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 22, bold=True)
    big = pygame.font.SysFont("arial", 56, bold=True)
    small = pygame.font.SysFont("arial", 18, bold=True)
    tiny = pygame.font.SysFont("arial", 13, bold=True)

    canvas = pygame.Surface((WIDTH, HEIGHT))
    bg = make_gradient()
    stars = [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT),
              random.uniform(0.2, 1.0), random.choice([1, 1, 2])] for _ in range(70)]

    # ----- state -----
    paddle = pygame.Rect(0, HEIGHT - 45, PADDLE_W, PADDLE_H)
    paddle.centerx = WIDTH // 2
    paddle_w = float(PADDLE_W)
    balls = []
    speed = BASE_SPEED
    particles = []   # [x, y, vx, vy, life, maxlife, color, size]
    popups = []      # [x, y, text, life, color]
    drops = []       # [x, y, kind]
    bullets = []     # [x, y]
    effects = {}     # kind -> sisa frame
    bricks = build_bricks()
    score, lives, level, combo = 0, 3, 1, 0
    shake = 0.0
    hue = 0.0
    laser_cd = 0
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

    def burst(x, y, color, n=16):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(1.5, 6)
            particles.append([x, y, math.cos(a) * s, math.sin(a) * s,
                              random.randint(20, 40), 40, color, random.uniform(2, 5)])

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
        popups.append([paddle.centerx, paddle.top - 20, name, 50, color])
        if kind == "multi":
            extra = []
            for b in balls:
                for ang in (-0.45, 0.45):
                    c, s = math.cos(ang), math.sin(ang)
                    extra.append(Ball(b.x, b.y, b.vx * c - b.vy * s, b.vx * s + b.vy * c))
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

        # lebar papan halus
        paddle_w += ((PADDLE_W * 1.5 if "wide" in effects else PADDLE_W) - paddle_w) * 0.15
        cx = paddle.centerx
        paddle.w = int(paddle_w)
        paddle.centerx = cx
        paddle.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

        # timer efek
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

                # paddle: sudut tergantung posisi benturan
                if rect.colliderect(paddle) and ball.vy > 0:
                    off = max(-1, min(1, (ball.x - paddle.centerx) / (paddle.w / 2)))
                    a = math.radians(270 + off * 60)
                    ball.vx, ball.vy = tgt * math.cos(a), tgt * math.sin(a)
                    ball.y = paddle.top - BALL_R
                    combo = 0
                    burst(ball.x, paddle.top, PADDLE_COLOR, 6)

                # brick
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

                # bola jatuh
                if ball.y - BALL_R > HEIGHT:
                    balls.remove(ball)

            # semua bola jatuh -> nyawa berkurang
            if not balls:
                lives -= 1
                combo = 0
                shake = 12
                burst(paddle.centerx, HEIGHT - 10, (255, 80, 80), 30)
                clear_extras()
                reset_ball()
                state = "lost" if lives <= 0 else "ready"

            # laser otomatis
            if state == "playing" and "laser" in effects:
                laser_cd -= 1
                if laser_cd <= 0:
                    bullets.append([paddle.left + 8, paddle.top])
                    bullets.append([paddle.right - 8, paddle.top])
                    laser_cd = 20

            # peluru
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

            # power-up jatuh
            for d in drops[:]:
                d[1] += 2.6
                drect = pygame.Rect(d[0] - 29, d[1] - 11, 58, 22)
                if drect.colliderect(paddle):
                    apply_powerup(d[2])
                    drops.remove(d)
                elif d[1] > HEIGHT + 20:
                    drops.remove(d)

            # level selesai
            if not bricks and state == "playing":
                level += 1
                speed = min(MAX_SPEED, BASE_SPEED + 0.6 * (level - 1))
                bricks = build_bricks()
                clear_extras()
                reset_ball()
                state = "ready"
                popups.append([WIDTH // 2, HEIGHT // 2, f"LEVEL {level}!", 70, (255, 255, 120)])

        # partikel & popup
        for p in particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.15
            p[4] -= 1
        particles[:] = [p for p in particles if p[4] > 0]
        for t in popups:
            t[1] -= 0.8
            t[3] -= 1
        popups[:] = [t for t in popups if t[3] > 0]
        for s in stars:
            s[1] += s[2]
            if s[1] > HEIGHT:
                s[0], s[1] = random.uniform(0, WIDTH), 0
        shake *= 0.85

        # ----- Gambar -----
        canvas.blit(bg, (0, 0))
        for s in stars:
            v = int(120 + 100 * s[2])
            pygame.draw.circle(canvas, (v, v, 255), (int(s[0]), int(s[1])), s[3])

        for b in bricks:
            b.draw(canvas)

        # jejak & bola
        fire = "fire" in effects
        for ball in balls:
            n = len(ball.trail)
            for i, (tx, ty) in enumerate(ball.trail):
                k = (i + 1) / n
                col = (255, int(120 + 100 * k), 40) if fire else hue_color(hue - (n - i) * 8)
                pygame.draw.circle(canvas, col, (int(tx), int(ty)), max(1, int(BALL_R * k * 0.8)))
        for ball in balls:
            glow(canvas, (int(ball.x), int(ball.y)), 26,
                 (255, 150, 50) if fire else (255, 255, 255), 80)
            pygame.draw.circle(canvas, (255, 200, 90) if fire else (255, 255, 255),
                               (int(ball.x), int(ball.y)), BALL_R)

        # papan (bersih: warna tetap + cahaya tipis)
        pc = (255, 160, 70) if fire else PADDLE_COLOR
        soft_rect_glow(canvas, paddle, pc)
        pygame.draw.rect(canvas, pc, paddle, border_radius=8)
        pygame.draw.rect(canvas, (255, 255, 255),
                         (paddle.x + 8, paddle.y + 3, paddle.w - 16, 3), border_radius=2)
        if "laser" in effects:
            for lx in (paddle.left + 4, paddle.right - 12):
                pygame.draw.rect(canvas, (255, 70, 70), (lx, paddle.top - 7, 8, 9), border_radius=2)

        # peluru laser
        for bl in bullets:
            pygame.draw.rect(canvas, (255, 110, 110), (bl[0] - 2, bl[1], 4, 14), border_radius=2)

        # power-up jatuh
        for d in drops:
            name, col, _, _ = POWERUPS[d[2]]
            r = pygame.Rect(0, 0, 58, 22)
            r.center = (int(d[0]), int(d[1]))
            glow(canvas, r.center, 34, col, 60)
            pygame.draw.rect(canvas, col, r, border_radius=11)
            pygame.draw.rect(canvas, (255, 255, 255), r, 2, border_radius=11)
            text_center(canvas, tiny, name, r.center, (20, 15, 40))

        for p in particles:
            a = p[4] / p[5]
            pygame.draw.circle(canvas, tuple(int(c * a) for c in p[6]),
                               (int(p[0]), int(p[1])), max(1, int(p[7] * a)))
        for t in popups:
            text_center(canvas, font, t[2], (t[0], t[1]), t[4])

        # HUD
        canvas.blit(font.render(f"Skor: {score}", True, (255, 255, 255)), (14, 12))
        text_center(canvas, font, f"Level {level}", (WIDTH // 2, 24), (255, 230, 120))
        for i in range(lives):
            draw_heart(canvas, WIDTH - 30 - i * 34, 22, 9, (255, 80, 110))
        if combo >= 2:
            text_center(canvas, small, f"COMBO x{combo}", (WIDTH // 2, 50), hue_color(hue * 2))
        # bar efek aktif
        for i, (k, left) in enumerate(effects.items()):
            name, col, dur, _ = POWERUPS[k]
            y = 44 + i * 18
            canvas.blit(tiny.render(name, True, col), (14, y))
            pygame.draw.rect(canvas, (50, 45, 80), (74, y + 3, 90, 7), border_radius=3)
            pygame.draw.rect(canvas, col, (74, y + 3, int(90 * left / dur), 7), border_radius=3)

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