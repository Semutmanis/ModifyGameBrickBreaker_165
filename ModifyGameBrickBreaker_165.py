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

ROWS, COLS = 6, 10
GAP = 5
TOP = 70
BRICK_H = 24
TOUGH_CHANCE = 0.25  # brick yang butuh 2 pukulan

ROW_COLORS = [
    (255, 85, 110), (255, 150, 60), (255, 220, 70),
    (80, 230, 140), (70, 190, 255), (180, 110, 255),
]


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
    for r in range(radius, 0, -3):
        a = int(alpha * (1 - r / radius) ** 1.5) + 4
        pygame.draw.circle(g, (*color, min(255, a)), (radius, radius), r)
    surf.blit(g, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_PREMULTIPLIED)


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
        # kilau di bagian atas
        shine = pygame.Rect(self.rect.x + 3, self.rect.y + 3, self.rect.w - 6, self.rect.h // 3)
        light = tuple(min(255, v + 70) for v in c)
        pygame.draw.rect(surf, light, shine, border_radius=4)
        if self.tough:
            pygame.draw.rect(surf, (255, 255, 255), self.rect, 2, border_radius=6)
            if self.hp == 1:  # garis retak
                r = self.rect
                pygame.draw.lines(surf, (30, 20, 50), False, [
                    (r.x + r.w * 0.3, r.y + 2), (r.x + r.w * 0.45, r.centery),
                    (r.x + r.w * 0.35, r.bottom - 2)], 2)


def build_bricks():
    bricks = []
    bw = (WIDTH - GAP * (COLS + 1)) // COLS
    for r in range(ROWS):
        for c in range(COLS):
            rect = pygame.Rect(GAP + c * (bw + GAP), TOP + r * (BRICK_H + GAP), bw, BRICK_H)
            bricks.append(Brick(rect, ROW_COLORS[r % len(ROW_COLORS)], random.random() < TOUGH_CHANCE))
    return bricks


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Brick Breaker Warna-Warni")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 22, bold=True)
    big = pygame.font.SysFont("arial", 56, bold=True)
    small = pygame.font.SysFont("arial", 18, bold=True)

    canvas = pygame.Surface((WIDTH, HEIGHT))
    bg = make_gradient()
    stars = [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT),
              random.uniform(0.2, 1.0), random.choice([1, 1, 2])] for _ in range(70)]

    # state
    paddle = pygame.Rect(0, HEIGHT - 45, PADDLE_W, PADDLE_H)
    paddle.centerx = WIDTH // 2
    bx = by = 0.0
    vx = vy = 0.0
    speed = BASE_SPEED
    trail = []
    particles = []   # [x, y, vx, vy, life, maxlife, color, size]
    popups = []      # [x, y, text, life, color]
    bricks = build_bricks()
    score, lives, level, combo = 0, 3, 1, 0
    shake = 0.0
    hue = 0.0
    state = "ready"  # ready | playing | lost

    def launch_ball():
        nonlocal vx, vy
        a = math.radians(random.uniform(250, 290))
        vx, vy = speed * math.cos(a), speed * math.sin(a)

    def rescale():
        nonlocal vx, vy
        m = math.hypot(vx, vy) or 1
        vx, vy = vx / m * speed, vy / m * speed

    def burst(x, y, color, n=16):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(1.5, 6)
            particles.append([x, y, math.cos(a) * s, math.sin(a) * s,
                              random.randint(20, 40), 40, color, random.uniform(2, 5)])

    running = True
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
                        state = "ready"

        # ----- Input: tombol panah -----
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            paddle.x -= PADDLE_SPEED
        if keys[pygame.K_RIGHT]:
            paddle.x += PADDLE_SPEED
        paddle.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

        # ----- Update -----
        if state == "ready":
            bx, by = paddle.centerx, paddle.top - BALL_R - 1
            trail.clear()
        elif state == "playing":
            bx += vx
            by += vy
            trail.append((bx, by))
            if len(trail) > 14:
                trail.pop(0)

            if bx - BALL_R <= 0:
                bx, vx = BALL_R, abs(vx)
            elif bx + BALL_R >= WIDTH:
                bx, vx = WIDTH - BALL_R, -abs(vx)
            if by - BALL_R <= 0:
                by, vy = BALL_R, abs(vy)

            ball_rect = pygame.Rect(bx - BALL_R, by - BALL_R, BALL_R * 2, BALL_R * 2)

            # paddle: sudut tergantung posisi benturan
            if ball_rect.colliderect(paddle) and vy > 0:
                off = max(-1, min(1, (bx - paddle.centerx) / (paddle.w / 2)))
                a = math.radians(270 + off * 60)
                vx, vy = speed * math.cos(a), speed * math.sin(a)
                by = paddle.top - BALL_R
                combo = 0
                burst(bx, paddle.top, hue_color(hue), 6)

            # brick
            for b in bricks:
                if ball_rect.colliderect(b.rect):
                    ox = min(ball_rect.right - b.rect.left, b.rect.right - ball_rect.left)
                    oy = min(ball_rect.bottom - b.rect.top, b.rect.bottom - ball_rect.top)
                    if ox < oy:
                        vx *= -1
                    else:
                        vy *= -1
                    b.hp -= 1
                    shake = max(shake, 3)
                    if b.hp <= 0:
                        bricks.remove(b)
                        combo += 1
                        pts = 10 * combo
                        score += pts
                        burst(b.rect.centerx, b.rect.centery, b.color)
                        popups.append([b.rect.centerx, b.rect.centery, f"+{pts}", 40, b.color])
                        shake = max(shake, 6)
                        speed = min(MAX_SPEED, speed + 0.08)
                        rescale()
                    else:
                        burst(b.rect.centerx, b.rect.centery, (255, 255, 255), 6)
                    break

            # bola jatuh
            if by - BALL_R > HEIGHT:
                lives -= 1
                combo = 0
                shake = 12
                burst(bx, HEIGHT - 10, (255, 80, 80), 30)
                state = "lost" if lives <= 0 else "ready"

            # level selesai
            if not bricks and state == "playing":
                level += 1
                speed = min(MAX_SPEED, BASE_SPEED + 0.6 * (level - 1))
                bricks = build_bricks()
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

        # jejak bola
        for i, (tx, ty) in enumerate(trail):
            k = (i + 1) / len(trail)
            pygame.draw.circle(canvas, hue_color(hue - (len(trail) - i) * 8),
                               (int(tx), int(ty)), max(1, int(BALL_R * k * 0.8)))

        # paddle dengan glow
        pc = hue_color(hue)
        glow(canvas, paddle.center, 90, pc, 60)
        pygame.draw.rect(canvas, pc, paddle, border_radius=8)
        pygame.draw.rect(canvas, (255, 255, 255),
                         (paddle.x + 6, paddle.y + 2, paddle.w - 12, 4), border_radius=2)

        # bola dengan glow
        glow(canvas, (int(bx), int(by)), 28, (255, 255, 255), 90)
        pygame.draw.circle(canvas, (255, 255, 255), (int(bx), int(by)), BALL_R)

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