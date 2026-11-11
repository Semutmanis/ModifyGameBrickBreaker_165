import pygame
import random

# Inisialisasi Pygame
pygame.init()

# Dimensi Layar
WIDTH, HEIGHT = 600, 500

# Warna
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Pengaturan Font dan Layar
font = pygame.font.Font('freesansbold.ttf', 15)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Block Breaker")

# Pengontrol Frame Rate
clock = pygame.time.Clock()
FPS = 30


# --- FUNGSI BANTUAN ---

def collisionChecker(rect, ball):
    """Mengecek kolisi/tabrakan antara dua objek (misal: balok & bola)."""
    if pygame.Rect.colliderect(rect, ball):
        return True
    return False


def populateBlocks(blockWidth, blockHeight, horizontalGap, verticalGap):
    """Membuat daftar balok/brick di area atas layar."""
    listOfBlocks = []
    for i in range(0, WIDTH, blockWidth + horizontalGap):
        for j in range(0, HEIGHT // 2, blockHeight + verticalGap):
            listOfBlocks.append(Block(i, j, blockWidth,
                                      blockHeight, 
                                      random.choice([WHITE, GREEN])))
    return listOfBlocks


def gameOver():
    """Menampilkan mode layar akhir ketika nyawa habis."""
    gameOverState = True
    while gameOverState:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return True


# --- KELAS OBJEK ---

class Striker:
    """Papan pemukul (paddle) yang dikontrol pemain."""
    def __init__(self, posx, posy, width, height, speed, color):
        self.posx, self.posy = posx, posy
        self.width, self.height = width, height
        self.speed = speed
        self.color = color
        self.strikerRect = pygame.Rect(
            self.posx, self.posy, self.width, self.height)
        self.striker = pygame.draw.rect(screen, self.color, self.strikerRect)

    def display(self):
        self.striker = pygame.draw.rect(screen, self.color, self.strikerRect)

    def update(self, xFac):
        self.posx += self.speed * xFac
        # Batasi gerakan agar tidak keluar layar
        if self.posx <= 0:
            self.posx = 0
        elif self.posx + self.width >= WIDTH:
            self.posx = WIDTH - self.width
        self.strikerRect = pygame.Rect(
            self.posx, self.posy, self.width, self.height)

    def getRect(self):
        return self.strikerRect


class Block:
    """Balok yang harus dihancurkan bola."""
    def __init__(self, posx, posy, width, height, color):
        self.posx, self.posy = posx, posy
        self.width, self.height = width, height
        self.color = color
        self.damage = 100
        
        # Balok putih butuh 2x pukulan, balok hijau 1x pukulan
        if color == WHITE:
            self.health = 200
        else:
            self.health = 100

        self.blockRect = pygame.Rect(
            self.posx, self.posy, self.width, self.height)
        self.block = pygame.draw.rect(screen, self.color, self.blockRect)

    def display(self):
        if self.health > 0:
            self.brick = pygame.draw.rect(screen, self.color, self.blockRect)

    def hit(self):
        self.health -= self.damage

    def getRect(self):
        return self.blockRect

    def getHealth(self):
        return self.health


class Ball:
    """Bola pantul."""
    def __init__(self, posx, posy, radius, speed, color):
        self.posx, self.posy = posx, posy
        self.radius = radius
        self.speed = speed
        self.color = color
        self.xFac, self.yFac = 1, 1
        self.ball = pygame.draw.circle(screen, self.color, (self.posx, self.posy), self.radius)

    def display(self):
        self.ball = pygame.draw.circle(screen, self.color, (self.posx, self.posy), self.radius)

    def update(self):
        self.posx += self.xFac * self.speed
        self.posy += self.yFac * self.speed

        # Pantulan dari dinding kiri & kanan
        if self.posx <= 0 or self.posx >= WIDTH:
            self.xFac *= -1
        # Pantulan dari atas
        if self.posy <= 0:
            self.yFac *= -1
        # Mengembalikan True jika bola menyentuh batas bawah (nyawa berkurang)
        if self.posy >= HEIGHT:
            return True
        return False

    def reset(self):
        self.posx = 0
        self.posy = HEIGHT
        self.xFac, self.yFac = 1, -1

    def hit(self):
        self.yFac *= -1

    def getRect(self):
        return self.ball


# --- FUNGSI UTAMA (GAME LOOP) ---

def main():
    running = True
    lives = 3
    score = 0

    scoreText = font.render("Score : " + str(score), True, WHITE)
    scoreTextRect = scoreText.get_rect()
    scoreTextRect.center = (40, HEIGHT - 10)

    livesText = font.render("Lives : " + str(lives), True, WHITE)
    livesTextRect = livesText.get_rect()
    livesTextRect.center = (120, HEIGHT - 10)

    striker = Striker(0, HEIGHT - 50, 100, 20, 10, WHITE)
    strikerXFac = 0
    ball = Ball(0, HEIGHT - 150, 7, 5, WHITE)

    blockWidth, blockHeight = 40, 15
    horizontalGap, verticalGap = 20, 20
    listOfBlocks = populateBlocks(
        blockWidth, blockHeight, horizontalGap, verticalGap)

    # Game Loop
    while running:
        screen.fill(BLACK)

        # Jika semua balok habis, buat ulang baloknya
        if not listOfBlocks:
            listOfBlocks = populateBlocks(
                blockWidth, blockHeight, horizontalGap, verticalGap)

        # Jika nyawa habis
        if lives <= 0:
            running = gameOver()
            listOfBlocks.clear()
            lives = 3
            score = 0
            listOfBlocks = populateBlocks(
                blockWidth, blockHeight, horizontalGap, verticalGap)

        # Deteksi Input / Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    strikerXFac = -1
                if event.key == pygame.K_RIGHT:
                    strikerXFac = 1
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    strikerXFac = 0

        # Cek Benturan Papan Pemukul & Bola
        if collisionChecker(striker.getRect(), ball.getRect()):
            ball.hit()

        # Cek Benturan Balok & Bola
        for block in listOfBlocks:
            if collisionChecker(block.getRect(), ball.getRect()):
                ball.hit()
                block.hit()
                if block.getHealth() <= 0:
                    listOfBlocks.remove(block)
                    score += 5

        # Update Posisi Objek
        striker.update(strikerXFac)
        lifeLost = ball.update()
        if lifeLost:
            lives -= 1
            ball.reset()

        # Update Teks
        scoreText = font.render("Score : " + str(score), True, WHITE)
        livesText = font.render("Lives : " + str(lives), True, WHITE)
        screen.blit(scoreText, scoreTextRect)
        screen.blit(livesText, livesTextRect)

        # Render / Display Objek
        striker.display()
        ball.display()
        for block in listOfBlocks:
            block.display()

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()


# Jalankan Game
if __name__ == "__main__":
    main()