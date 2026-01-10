import cv2
import mediapipe as mp
import numpy as np
import random
import time
import math
import pygame
import os
import json
from datetime import datetime

# pip install opencv-python mediapipe numpy pygame

class Fruit:
    def __init__(self, screen_width, screen_height, images=None, speed_mult=1.0, direction='Down'):
        self.type = random.choice(['banana', 'orange'])
        self.radius = 30
        self.images = images
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.direction = direction
        
        base_speed = random.uniform(5, 10)
        self.speed = base_speed * speed_mult
        
        # Initial Position logic based on direction
        if self.direction == 'Up':
            self.x = random.randint(50, screen_width - 50)
            self.y = screen_height + 50 # Start below screen
        elif self.direction == 'Diagonal':
            # Start from top, but move sideways too
            self.x = random.randint(50, screen_width - 50)
            self.y = -50
            self.dx = random.choice([-1, 1]) * (self.speed * 0.5)
        else: # Down
            self.x = random.randint(50, screen_width - 50)
            self.y = -50 # Start above screen

        if self.type == 'banana':
            self.color = (0, 255, 255) # Yellow
        else:
            self.color = (0, 165, 255) # Orange

    def update(self):
        if self.direction == 'Up':
            self.y -= self.speed
        elif self.direction == 'Diagonal':
            self.y += self.speed
            self.x += self.dx
            # Bounce off walls
            if self.x < 0 or self.x > self.screen_width:
                self.dx *= -1
        else: # Down
            self.y += self.speed

    def draw(self, image):
        img_to_draw = None
        if self.images and self.type in self.images:
            img_to_draw = self.images[self.type]

        if img_to_draw is not None:
            h, w, _ = img_to_draw.shape
            x_pos = int(self.x - w // 2)
            y_pos = int(self.y - h // 2)
            
            y1, y2 = max(0, y_pos), min(image.shape[0], y_pos + h)
            x1, x2 = max(0, x_pos), min(image.shape[1], x_pos + w)
            
            y1o, y2o = max(0, -y_pos), min(h, image.shape[0] - y_pos)
            x1o, x2o = max(0, -x_pos), min(w, image.shape[1] - x_pos)

            if y1 < y2 and x1 < x2:
                alpha_s = img_to_draw[y1o:y2o, x1o:x2o, 3] / 255.0
                alpha_l = 1.0 - alpha_s
                
                for c in range(0, 3):
                    image[y1:y2, x1:x2, c] = (alpha_s * img_to_draw[y1o:y2o, x1o:x2o, c] +
                                              alpha_l * image[y1:y2, x1:x2, c])
        else:
            cv2.circle(image, (int(self.x), int(self.y)), self.radius, self.color, -1)
            cv2.circle(image, (int(self.x), int(self.y)), self.radius, (255, 255, 255), 2)

class BodyCatchGame:
    def __init__(self):
        # 1. Camera & Display
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open webcam.")
            return

        self.width = 1280
        self.height = 720
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        # 2. Skeleton Detection
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

        # Game Settings
        self.settings = {
            'duration': {'options': [30, 60, 90, 120], 'idx': 1, 'label': 'Game Duration (s)'},
            'spawn_rate': {'options': [1.5, 1.0, 0.5, 0.3], 'idx': 1, 'label': 'Spawn Rate (s)'}, # Lower is faster
            'speed_mult': {'options': [0.5, 1.0, 1.5, 2.0], 'idx': 1, 'label': 'Fall Speed'},
            'direction': {'options': ['Down', 'Diagonal', 'Up'], 'idx': 0, 'label': 'Direction'}
        }
        
        # State: START, PLAYING, SETTINGS, GAMEOVER
        self.state = 'START'

        # Load Assets
        self.images = {}
        try:
            banana_img = cv2.imread('icon/banana.png', cv2.IMREAD_UNCHANGED)
            orange_img = cv2.imread('icon/orange.png', cv2.IMREAD_UNCHANGED)
            
            if banana_img is not None:
                if len(banana_img.shape) == 3 and banana_img.shape[2] == 3:
                    banana_img = cv2.cvtColor(banana_img, cv2.COLOR_BGR2BGRA)
                self.images['banana'] = cv2.resize(banana_img, (60, 60))
                
            if orange_img is not None:
                if len(orange_img.shape) == 3 and orange_img.shape[2] == 3:
                    orange_img = cv2.cvtColor(orange_img, cv2.COLOR_BGR2BGRA)
                self.images['orange'] = cv2.resize(orange_img, (60, 60))
        except Exception as e:
            print(f"Error loading images: {e}")

        # Initialize Music
        try:
            pygame.mixer.init()
            if os.path.exists('techno.mp3'):
                pygame.mixer.music.load('techno.mp3')
                # Play continuously (-1 means loop indefinitely)
                pygame.mixer.music.play(-1)
                print("Playing techno.mp3")
            else:
                print("techno.mp3 not found. Music will not play.")
        except Exception as e:
            print(f"Error initializing music: {e}")

        # Load High Scores
        self.high_scores = self.load_high_scores()
        
        # Game Variables
        self.reset_game_state()

    def reset_game_state(self):
        self.score = 0
        self.start_time = time.time()
        
        # Apply Settings
        self.game_duration = self.settings['duration']['options'][self.settings['duration']['idx']]
        self.spawn_interval = self.settings['spawn_rate']['options'][self.settings['spawn_rate']['idx']]
        
        self.score_saved = False
        
        self.fruits = []
        self.effects = [] 
        self.last_spawn_time = time.time()

    def load_high_scores(self):
        if os.path.exists('highscores.json'):
            try:
                with open('highscores.json', 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_high_score(self):
        new_entry = {
            'score': self.score,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        self.high_scores.append(new_entry)
        self.high_scores.sort(key=lambda x: x['score'], reverse=True)
        self.high_scores = self.high_scores[:10]
        try:
            with open('highscores.json', 'w') as f:
                json.dump(self.high_scores, f, indent=4)
        except Exception as e:
            print(f"Error saving high scores: {e}")
        self.score_saved = True

    def spawn_fruit(self):
        speed = self.settings['speed_mult']['options'][self.settings['speed_mult']['idx']]
        direction = self.settings['direction']['options'][self.settings['direction']['idx']]
        self.fruits.append(Fruit(self.width, self.height, self.images, speed, direction))

    def detect_collision(self, x, y, points_value):
        caught_indices = []
        for i, fruit in enumerate(self.fruits):
            distance = math.sqrt((x - fruit.x)**2 + (y - fruit.y)**2)
            if distance < 50 + fruit.radius: 
                caught_indices.append(i)
                self.score += points_value
                self.effects.append([fruit.x, fruit.y, 10, 50])
        
        for i in sorted(caught_indices, reverse=True):
            del self.fruits[i]

    # --- Draw Screens ---

    def draw_start_screen(self, image):
        # Overlay
        cv2.rectangle(image, (0, 0), (self.width, self.height), (0, 0, 0), -1)
        
        cv2.putText(image, "BODY CATCH GAME", (self.width//2 - 300, 200), 
                    cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 0), 5)
        
        cv2.putText(image, "Press 'S' to START", (self.width//2 - 200, 350), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
        
        cv2.putText(image, "Press 'P' for SETTINGS", (self.width//2 - 220, 450), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        cv2.putText(image, "Press 'Q' or ESC to Quit", (self.width//2 - 200, 550), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2)

    def draw_settings_screen(self, image):
        cv2.rectangle(image, (0, 0), (self.width, self.height), (20, 20, 20), -1)
        
        cv2.putText(image, "SETTINGS", (self.width//2 - 150, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 4)

        y_off = 200
        keys = list(self.settings.keys())
        
        for idx, key in enumerate(keys):
            item = self.settings[key]
            val = item['options'][item['idx']]
            label = item['label']
            
            text = f"{idx+1}. {label}: {val}"
            cv2.putText(image, text, (self.width//2 - 300, y_off), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)
            y_off += 80

        cv2.putText(image, "Press Number Keys (1-4) to Cycle Options", (self.width//2 - 350, 550), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)

        cv2.putText(image, "Press 'B' or 'P' to Back", (self.width//2 - 200, 650), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

    def draw_ui(self, image):
        cv2.putText(image, f"Score: {self.score}", (30, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        elapsed_time = time.time() - self.start_time
        remaining_time = max(0, self.game_duration - int(elapsed_time))
        color = (255, 255, 255)
        if remaining_time <= 10:
            color = (0, 0, 255) 
        
        cv2.putText(image, f"Time: {remaining_time}", (30, 140), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)

        if remaining_time == 0:
            self.state = 'GAMEOVER'
            if not self.score_saved:
                self.save_high_score()

    def draw_game_over(self, image):
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, image, 0.15, 0, image)

        cv2.putText(image, "GAME OVER", (self.width//2 - 200, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 5)
        
        cv2.putText(image, f"Final Score: {self.score}", (self.width//2 - 150, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        cv2.putText(image, "Top 10 High Scores:", (self.width//2 - 250, 220), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 215, 0), 2)
        
        y_offset = 260
        for idx, entry in enumerate(self.high_scores):
            score_str = f"{idx+1}. {entry['score']} pts - {entry['time']}"
            cv2.putText(image, score_str, (self.width//2 - 250, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            y_offset += 30

        help_text1 = "Press 'R' to Restart"
        help_text2 = "Press 'P' for Settings"
        help_text3 = "Press 'Q' or ESC to Quit"
        
        cv2.putText(image, help_text1, (self.width//2 - 150, 600), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(image, help_text2, (self.width//2 - 150, 640), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(image, help_text3, (self.width//2 - 150, 680), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2)

    def run(self):
        while self.cap.isOpened():
            success, image = self.cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            image = cv2.flip(image, 1) # Mirror view
            
            # --- Input Handling ---
            key = cv2.waitKey(5) & 0xFF
            if key == 27 or key == ord('q'): # ESC or q
                break

            # Global Navigation
            if self.state == 'START':
                if key == ord('s'):
                    self.reset_game_state()
                    self.state = 'PLAYING'
                elif key == ord('p'):
                    self.state = 'SETTINGS'
                self.draw_start_screen(image)

            elif self.state == 'SETTINGS':
                if key == ord('b') or key == ord('p'): # Back
                    self.state = 'START' # Return to title normally, or maybe previous? Start is safe.
                
                # Settings adjustments
                keys = list(self.settings.keys()) # ['duration', 'spawn_rate', etc.]
                if key == ord('1'):
                    k = keys[0]
                    self.settings[k]['idx'] = (self.settings[k]['idx'] + 1) % len(self.settings[k]['options'])
                elif key == ord('2'):
                    k = keys[1]
                    self.settings[k]['idx'] = (self.settings[k]['idx'] + 1) % len(self.settings[k]['options'])
                elif key == ord('3'):
                    k = keys[2]
                    self.settings[k]['idx'] = (self.settings[k]['idx'] + 1) % len(self.settings[k]['options'])
                elif key == ord('4'):
                    k = keys[3]
                    self.settings[k]['idx'] = (self.settings[k]['idx'] + 1) % len(self.settings[k]['options'])
                
                self.draw_settings_screen(image)

            elif self.state == 'PLAYING':
                if key == ord('r'): # Restart mid-game
                    self.reset_game_state()

                # Game Logic
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                image_rgb.flags.writeable = False
                results = self.pose.process(image_rgb)
                image.flags.writeable = True

                if results.pose_landmarks:
                    self.mp_drawing.draw_landmarks(
                        image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                    
                    h, w, _ = image.shape
                    interaction_points = [
                        (self.mp_pose.PoseLandmark.NOSE, "Head", (0, 0, 255), 3),
                        (self.mp_pose.PoseLandmark.LEFT_WRIST, "L_Hand", (0, 255, 0), 1),
                        (self.mp_pose.PoseLandmark.RIGHT_WRIST, "R_Hand", (0, 255, 0), 1),
                        (self.mp_pose.PoseLandmark.LEFT_FOOT_INDEX, "L_Foot", (255, 0, 0), 2),
                        (self.mp_pose.PoseLandmark.RIGHT_FOOT_INDEX, "R_Foot", (255, 0, 0), 2)
                    ]

                    for lm_idx, name, color, points in interaction_points:
                        landmark = results.pose_landmarks.landmark[lm_idx]
                        if landmark.visibility > 0.5:
                            cx, cy = int(landmark.x * w), int(landmark.y * h)
                            cv2.circle(image, (cx, cy), 15, color, -1) 
                            self.detect_collision(cx, cy, points)

                # Fruits
                current_time = time.time()
                if current_time - self.last_spawn_time > self.spawn_interval:
                    self.spawn_fruit()
                    self.last_spawn_time = current_time
                
                for i in range(len(self.fruits) - 1, -1, -1):
                    fruit = self.fruits[i]
                    fruit.update()
                    fruit.draw(image)
                    
                    # Removal condition depends on direction, easier to just check if far out of bounds
                    # But kept simple: if it goes too far down or up
                    remove = False
                    if fruit.direction == 'Up':
                         if fruit.y < -50: remove = True
                    else:
                         if fruit.y > self.height + 50: remove = True
                    
                    if remove:
                        del self.fruits[i]

                # Effects
                for i in range(len(self.effects) - 1, -1, -1):
                    ex, ey, r, max_r = self.effects[i]
                    if r < max_r:
                        cv2.circle(image, (int(ex), int(ey)), int(r), (255, 255, 255), 3)
                        self.effects[i][2] += 5 
                    else:
                        del self.effects[i]
                
                self.draw_ui(image)

            elif self.state == 'GAMEOVER':
                if key == ord('r'):
                    self.reset_game_state()
                    self.state = 'PLAYING'
                elif key == ord('p'):
                    self.state = 'SETTINGS'
                
                self.draw_game_over(image)

            cv2.imshow('Body Catch Game', image)
        
        try:
            pygame.mixer.music.stop()
        except:
            pass
            
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = BodyCatchGame()
    game.run()
