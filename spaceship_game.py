import pygame
import cv2
import numpy as np
import mediapipe as mp
import math
import time

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)

GAME_PLAYING = 0
GAME_OVER = 1

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Spaceship Gesture Control")
clock = pygame.time.Clock()

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        
        self.velocity_x = 0
        self.acceleration = 0.5
        self.deceleration = 0.95
        self.max_speed = 8

        self.fire_rate = 300
        self.last_shot_time = pygame.time.get_ticks()

        self.is_power_up_active = False
        self.power_up_start_time = 0
        self.power_up_duration = 5000
        self.is_accelerating = False
    
    def update(self, target_x_position=None):
        self.is_accelerating = False
        if target_x_position is not None:
            if target_x_position < self.rect.centerx - 20:
                self.velocity_x -= self.acceleration
                self.is_accelerating = True
            elif target_x_position > self.rect.centerx + 20:
                self.velocity_x += self.acceleration
                self.is_accelerating = True
            else:
                self.velocity_x *= self.deceleration
        else:
            self.velocity_x *= self.deceleration

        self.velocity_x = max(-self.max_speed, min(self.velocity_x, self.max_speed))
        
        self.rect.x += self.velocity_x
        
        if self.rect.left < 0:
            self.rect.left = 0
            self.velocity_x = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.velocity_x = 0

        if self.is_power_up_active and pygame.time.get_ticks() - self.power_up_start_time > self.power_up_duration:
            self.is_power_up_active = False
            self.fire_rate = 300

    def shoot(self):
        current_time = pygame.time.get_ticks()
        effective_fire_rate = self.fire_rate / (2 if self.is_power_up_active else 1)
        if current_time - self.last_shot_time > effective_fire_rate:
            projectile = Projectile(self.rect.centerx, self.rect.top)
            all_sprites.add(projectile)
            projectiles_group.add(projectile)
            self.last_shot_time = current_time

    def activate_power_up(self):
        if not self.is_power_up_active:
            self.is_power_up_active = True
            self.power_up_start_time = pygame.time.get_ticks()

    def draw(self, screen):
        color = YELLOW if self.is_power_up_active else BLUE
        
        points = [
            (self.rect.centerx, self.rect.top),
            (self.rect.left, self.rect.bottom),
            (self.rect.centerx, self.rect.bottom - 10),
            (self.rect.right, self.rect.bottom)
        ]
        
        pygame.draw.polygon(screen, color, points)
        
        if self.is_accelerating:
            thruster_points = [
                (self.rect.centerx, self.rect.bottom - 5),
                (self.rect.centerx - 10, self.rect.bottom + 10),
                (self.rect.centerx + 10, self.rect.bottom + 10)
            ]
            pygame.draw.polygon(screen, RED, thruster_points)


class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((5, 15), pygame.SRCALPHA)
        self.image.fill(WHITE)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = -10

    def update(self, *args, **kwargs):
        self.rect.y += self.speed
        if self.rect.bottom < 0:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((40, 40), pygame.SRCALPHA)
        self.image.fill(RED)
        self.rect = self.image.get_rect(center=(np.random.randint(50, SCREEN_WIDTH - 50), 0))
        self.speed = np.random.randint(1, 4)

    def update(self, *args, **kwargs):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Try to capture from a few different indices to be safe
cap = None
for i in range(3):
    try:
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Successfully opened webcam with index {i}.")
            break
    except:
        print(f"Failed to open webcam with index {i}. Trying next...")
        continue

if not cap or not cap.isOpened():
    print("FATAL ERROR: Could not open any webcam. Please ensure your camera is connected and not in use by another application.")
    pygame.quit()
    cv2.destroyAllWindows()
    exit()

def get_hand_landmarks(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(image_rgb)
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            return hand_landmarks
    return None

def get_landmark_coords(hand_landmarks, landmark_id, frame_width, frame_height):
    if hand_landmarks:
        lm = hand_landmarks.landmark[landmark_id]
        x = int(lm.x * frame_width)
        y = int(lm.y * frame_height)
        return (x, y)
    return None

def is_fist(hand_landmarks):
    if hand_landmarks:
        if (hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y > hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y and
            hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y > hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y and
            hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y > hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].y and
            hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y > hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].y):
            return True
    return False

THUMB_INDEX_PROXIMITY_THRESHOLD = 0.08

_thumb_tapped_in_prev_frame = False

def is_thumb_tapping(hand_landmarks):
    global _thumb_tapped_in_prev_frame
    if hand_landmarks:
        thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
        index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
        
        distance = math.sqrt((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)
        
        is_currently_close = distance < THUMB_INDEX_PROXIMITY_THRESHOLD
        
        if is_currently_close and not _thumb_tapped_in_prev_frame:
            _thumb_tapped_in_prev_frame = True
            return True
        elif not is_currently_close:
            _thumb_tapped_in_prev_frame = False
    return False

def is_middle_finger_up(hand_landmarks):
    if hand_landmarks:
        middle_tip_y = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
        middle_pip_y = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
        
        if middle_tip_y < middle_pip_y - 0.05:
            index_tip_y = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y
            ring_tip_y = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y
            pinky_tip_y = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y
            
            index_mcp_y = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
            ring_mcp_y = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].y
            pinky_mcp_y = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].y

            if (index_tip_y > index_mcp_y and
                ring_tip_y > ring_mcp_y and
                pinky_tip_y > pinky_mcp_y):
                return True
    return False

all_sprites = pygame.sprite.Group()
players_group = pygame.sprite.Group()
projectiles_group = pygame.sprite.Group()
enemies_group = pygame.sprite.Group()

player = Player()
all_sprites.add(player)
players_group.add(player)

score = 0
last_enemy_spawn_time = pygame.time.get_ticks()
enemy_spawn_delay = 1000

game_state = GAME_PLAYING

def reset_game():
    global score, last_enemy_spawn_time, game_state
    
    score = 0
    last_enemy_spawn_time = pygame.time.get_ticks()
    game_state = GAME_PLAYING
    
    for sprite in all_sprites:
        sprite.kill()
    
    player.__init__()
    all_sprites.add(player)
    players_group.add(player)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and game_state == GAME_PLAYING:
                player.shoot()
            if event.key == pygame.K_RETURN and game_state == GAME_OVER:
                reset_game()
        if event.type == pygame.KEYDOWN and game_state == GAME_PLAYING:
            if event.key == pygame.K_SPACE:
                player.shoot()

    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame. Reconnecting...")
        cap.release()
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f"Successfully reconnected with index {i}.")
                break
        if not cap or not cap.isOpened():
            print("Fatal error: Could not re-establish webcam connection. Exiting.")
            running = False
            break
        continue

    frame = cv2.flip(frame, 1)
    frame_height, frame_width, _ = frame.shape
    
    hand_landmarks = get_hand_landmarks(frame)
    
    player_target_x = None
    
    gesture_text = ""

    if hand_landmarks:
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        if game_state == GAME_PLAYING:
            wrist_coords = get_landmark_coords(hand_landmarks, mp_hands.HandLandmark.WRIST, frame_width, frame_height)
            if wrist_coords:
                player_target_x = wrist_coords[0]

            if is_thumb_tapping(hand_landmarks):
                player.shoot()
                gesture_text = "FIRE!"
            
            if is_fist(hand_landmarks):
                player.activate_power_up()
                gesture_text = "POWER-UP!"
        
        elif game_state == GAME_OVER:
            if is_middle_finger_up(hand_landmarks):
                gesture_text = "RESTARTING!"
                reset_game()

    if gesture_text:
        cv2.putText(frame, gesture_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA)

    if game_state == GAME_PLAYING:
        player.update(player_target_x) 
        projectiles_group.update() 
        enemies_group.update()

        current_time = pygame.time.get_ticks()
        if current_time - last_enemy_spawn_time > enemy_spawn_delay:
            enemy = Enemy()
            all_sprites.add(enemy)
            enemies_group.add(enemy)
            last_enemy_spawn_time = current_time

        hits = pygame.sprite.groupcollide(projectiles_group, enemies_group, True, True)
        for hit in hits:
            score += 10

        player_hits = pygame.sprite.spritecollide(player, enemies_group, True)
        if player_hits:
            game_state = GAME_OVER

    screen.fill(BLACK)
    
    player.draw(screen)
    projectiles_group.draw(screen)
    enemies_group.draw(screen)

    font = pygame.font.Font(None, 36)
    text_surface = font.render(f"Score: {score}", True, WHITE)
    screen.blit(text_surface, (10, 10))

    if game_state == GAME_OVER:
        game_over_font = pygame.font.Font(None, 72)
        game_over_text = game_over_font.render("GAME OVER", True, RED)
        restart_text = font.render("Press ENTER or show Middle Finger to Restart", True, WHITE)
        
        text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(game_over_text, text_rect)
        
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        screen.blit(restart_text, restart_rect)

    cv_display_width = 240
    cv_display_height = 180
    display_frame = cv2.resize(frame, (cv_display_width, cv_display_height))
    
    display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
    pygame_frame = pygame.surfarray.make_surface(display_frame.swapaxes(0, 1))
    
    screen.blit(pygame_frame, (SCREEN_WIDTH - cv_display_width - 10, 10))

    pygame.display.flip()
    clock.tick(FPS)

cap.release()
cv2.destroyAllWindows()
