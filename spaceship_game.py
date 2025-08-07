import pygame
import cv2
import numpy as np
import mediapipe as mp
import math
import time
import csv
import os

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)

GET_PLAYER_INFO = 0
GAME_PLAYING = 1
GAME_OVER = 2

pygame.init()

infoObject = pygame.display.Info()
FULL_SCREEN_WIDTH = infoObject.current_w
FULL_SCREEN_HEIGHT = infoObject.current_h
screen = pygame.display.set_mode((FULL_SCREEN_WIDTH, FULL_SCREEN_HEIGHT), pygame.NOFRAME)

pygame.display.set_caption("Spaceship Gesture Control")
clock = pygame.time.Clock()
FPS = 60

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(FULL_SCREEN_WIDTH // 2, FULL_SCREEN_HEIGHT - 50))
        
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
        if self.rect.right > FULL_SCREEN_WIDTH:
            self.rect.right = FULL_SCREEN_WIDTH
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
        self.rect = self.image.get_rect(center=(np.random.randint(50, FULL_SCREEN_WIDTH - 50), 0))
        self.speed = np.random.randint(1, 4)

    def update(self, *args, **kwargs):
        self.rect.y += self.speed
        if self.rect.top > FULL_SCREEN_HEIGHT:
            self.kill()

class WhiteCircle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.radius = 20
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, WHITE, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect(center=(np.random.randint(50, FULL_SCREEN_WIDTH - 50), 0))
        self.speed = np.random.randint(2, 5)

    def update(self, *args, **kwargs):
        self.rect.y += self.speed
        if self.rect.top > FULL_SCREEN_HEIGHT:
            self.kill()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = None
for i in range(3):
    try:
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            break
    except:
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

all_sprites = pygame.sprite.Group()
players_group = pygame.sprite.Group()
projectiles_group = pygame.sprite.Group()
enemies_group = pygame.sprite.Group()
white_circles_group = pygame.sprite.Group()

player = Player()
all_sprites.add(player)
players_group.add(player)

score = 0
player_name = ""
app_no = ""
input_stage = 0

game_timer_start = 0
game_timer_duration = 30
last_enemy_spawn_time = pygame.time.get_ticks()
enemy_spawn_delay = 1000
last_white_circle_spawn_time = pygame.time.get_ticks()
white_circle_spawn_delay = 2000

game_state = GET_PLAYER_INFO

def reset_game():
    global score, last_enemy_spawn_time, last_white_circle_spawn_time, game_state, game_timer_start, enemy_spawn_delay, white_circle_spawn_delay
    
    score = 0
    last_enemy_spawn_time = pygame.time.get_ticks()
    last_white_circle_spawn_time = pygame.time.get_ticks()
    game_state = GAME_PLAYING
    game_timer_start = pygame.time.get_ticks()
    enemy_spawn_delay = 1000
    white_circle_spawn_delay = 2000
    
    for sprite in all_sprites:
        sprite.kill()
    
    player.__init__()
    all_sprites.add(player)
    players_group.add(player)

def save_score():
    global player_name, app_no, score
    file_exists = os.path.isfile('high_scores.csv')
    try:
        with open('high_scores.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(['Player Name', 'Application No.', 'Score'])
            writer.writerow([player_name, app_no, score])
        print(f"Score saved for {player_name} (App No: {app_no}): {score}")
    except Exception as e:
        print(f"Error saving score: {e}")

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_state == GET_PLAYER_INFO:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if input_stage == 0 and len(player_name) > 0:
                        input_stage = 1
                    elif input_stage == 1 and len(app_no) > 0:
                        reset_game()
                elif event.key == pygame.K_BACKSPACE:
                    if input_stage == 0:
                        player_name = player_name[:-1]
                    else:
                        app_no = app_no[:-1]
                else:
                    if input_stage == 0:
                        player_name += event.unicode
                    else:
                        app_no += event.unicode
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if input_stage == 1 and start_button_rect.collidepoint(event.pos):
                    reset_game()
        
        elif game_state == GAME_OVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                player_name = ""
                app_no = ""
                input_stage = 0
                game_state = GET_PLAYER_INFO

        elif game_state == GAME_PLAYING:
            if event.type == pygame.KEYDOWN:
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
    
    if gesture_text:
        cv2.putText(frame, gesture_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA)

    screen.fill(BLACK)
    
    if game_state == GET_PLAYER_INFO:
        font = pygame.font.Font(None, 48)
        
        if input_stage == 0:
            prompt = "Enter your name:"
            input_text = player_name
            current_input = player_name
        else:
            prompt = "Enter Application No.:"
            input_text = app_no
            current_input = app_no
        
        prompt_surface = font.render(prompt, True, WHITE)
        prompt_rect = prompt_surface.get_rect(center=(FULL_SCREEN_WIDTH // 2, FULL_SCREEN_HEIGHT // 2 - 100))
        screen.blit(prompt_surface, prompt_rect)
        
        input_box = pygame.Rect(FULL_SCREEN_WIDTH // 2 - 200, FULL_SCREEN_HEIGHT // 2, 400, 50)
        pygame.draw.rect(screen, WHITE, input_box, 2)
        
        input_surface = font.render(input_text, True, WHITE)
        screen.blit(input_surface, (input_box.x + 5, input_box.y + 5))
        input_box.w = max(400, input_surface.get_width() + 10)
        
        cursor_pos = (input_box.x + 5 + input_surface.get_width(), input_box.y + 5)
        if time.time() % 1 > 0.5:
            pygame.draw.line(screen, WHITE, cursor_pos, (cursor_pos[0], cursor_pos[1] + font.get_height()), 2)
        
        start_button_rect = pygame.Rect(0, 0, 250, 60)
        start_button_rect.center = (FULL_SCREEN_WIDTH // 2, FULL_SCREEN_HEIGHT // 2 + 100)
        
        if input_stage == 1 and len(current_input) > 0:
            pygame.draw.rect(screen, BLUE, start_button_rect, 0, 10)
            start_button_text = font.render("Start Game", True, WHITE)
            start_text_rect = start_button_text.get_rect(center=start_button_rect.center)
            screen.blit(start_button_text, start_text_rect)

    elif game_state == GAME_PLAYING:
        player.update(player_target_x) 
        projectiles_group.update() 
        enemies_group.update()
        white_circles_group.update()

        current_time = pygame.time.get_ticks()
        
        if current_time - last_enemy_spawn_time > enemy_spawn_delay:
            if np.random.rand() > 0.5:
                enemy = Enemy()
                all_sprites.add(enemy)
                enemies_group.add(enemy)
            last_enemy_spawn_time = current_time
        
        if current_time - last_white_circle_spawn_time > white_circle_spawn_delay:
            if np.random.rand() > 0.7:
                white_circle = WhiteCircle()
                all_sprites.add(white_circle)
                white_circles_group.add(white_circle)
            last_white_circle_spawn_time = current_time

        # Increase difficulty after 15 seconds
        if (current_time - game_timer_start) // 1000 > 15 and (current_time - game_timer_start) // 1000 < 16:
            enemy_spawn_delay = 500
            white_circle_spawn_delay = 1000
            
        hits = pygame.sprite.groupcollide(projectiles_group, enemies_group, True, True)
        for hit in hits:
            score += 10

        player_hits = pygame.sprite.spritecollide(player, enemies_group, True)
        if player_hits:
            save_score()
            game_state = GAME_OVER

        white_circle_hits = pygame.sprite.spritecollide(player, white_circles_group, True)
        if white_circle_hits:
            score -= 10
            if score < 0:
                score = 0

        elapsed_time = (pygame.time.get_ticks() - game_timer_start) // 1000
        remaining_time = game_timer_duration - elapsed_time
        
        screen.fill(BLACK)
        player.draw(screen)
        projectiles_group.draw(screen)
        enemies_group.draw(screen)
        
        white_circles_group.draw(screen)
        
        font = pygame.font.Font(None, 36)
        text_surface = font.render(f"Score: {score}", True, WHITE)
        screen.blit(text_surface, (10, 10))
        
        timer_surface = font.render(f"Time: {remaining_time}s", True, WHITE)
        screen.blit(timer_surface, (10, 50))
        
        if remaining_time <= 0:
            remaining_time = 0
            save_score()
            game_state = GAME_OVER

    elif game_state == GAME_OVER:
        screen.fill(BLACK)
        game_over_font = pygame.font.Font(None, 72)
        game_over_text = game_over_font.render("GAME OVER", True, RED)
        restart_text = font.render("Press ENTER to Restart", True, WHITE)
        name_text = font.render(f"Player: {player_name}", True, WHITE)
        app_text = font.render(f"App No.: {app_no}", True, WHITE)
        score_text = font.render(f"Final Score: {score}", True, WHITE)
        
        text_rect = game_over_text.get_rect(center=(FULL_SCREEN_WIDTH // 2, FULL_SCREEN_HEIGHT // 2 - 150))
        screen.blit(game_over_text, text_rect)
        
        name_rect = name_text.get_rect(center=(FULL_SCREEN_WIDTH // 2, FULL_SCREEN_HEIGHT // 2 - 70))
        screen.blit(name_text, name_rect)

        app_rect = app_text.get_rect(center=(FULL_SCREEN_WIDTH // 2, FULL_SCREEN_HEIGHT // 2 - 20))
        screen.blit(app_text, app_rect)
        
        score_rect = score_text.get_rect(center=(FULL_SCREEN_WIDTH // 2, FULL_SCREEN_HEIGHT // 2 + 30))
        screen.blit(score_text, score_rect)
        
        restart_rect = restart_text.get_rect(center=(FULL_SCREEN_WIDTH // 2, FULL_SCREEN_HEIGHT // 2 + 100))
        screen.blit(restart_text, restart_rect)

    cv_display_width = 240
    cv_display_height = 180
    
    cv_feed = pygame.transform.scale(pygame.surfarray.make_surface(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).swapaxes(0, 1)), (cv_display_width, cv_display_height))
    screen.blit(cv_feed, (FULL_SCREEN_WIDTH - cv_display_width - 10, 10))
    
    pygame.display.flip()
    clock.tick(FPS)

cap.release()
cv2.destroyAllWindows()
