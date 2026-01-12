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

        # Game Modes
        self.MODE_FREE = 'FREE'
        self.MODE_STORY = 'STORY'
        self.current_mode = self.MODE_FREE

        # Free Mode Settings
        self.free_settings = {
            'duration': {'options': [30, 60, 90, 120], 'idx': 1, 'label': 'Game Duration (s)'},
            'spawn_rate': {'options': [1.5, 1.0, 0.5, 0.3], 'idx': 1, 'label': 'Spawn Rate (s)'}, 
            'speed_mult': {'options': [0.5, 1.0, 1.5, 2.0], 'idx': 1, 'label': 'Fall Speed'},
            'direction': {'options': ['Down', 'Diagonal', 'Up'], 'idx': 0, 'label': 'Direction'}
        }

        # Story Mode Config (List of 5 stages)
        # Default progression
        self.story_config = [
            # Stage 1: Easy
            {'duration': 30, 'spawn_rate': 1.5, 'speed_mult': 0.5, 'direction': 'Down'},
            # Stage 2: Normal
            {'duration': 45, 'spawn_rate': 1.0, 'speed_mult': 1.0, 'direction': 'Down'},
            # Stage 3: Faster
            {'duration': 60, 'spawn_rate': 1.0, 'speed_mult': 1.5, 'direction': 'Diagonal'},
            # Stage 4: Hard
            {'duration': 60, 'spawn_rate': 0.5, 'speed_mult': 1.5, 'direction': 'Diagonal'},
            # Stage 5: Expert
            {'duration': 90, 'spawn_rate': 0.3, 'speed_mult': 2.0, 'direction': 'Up'}
        ]
        self.current_stage = 0 
        
        # Helper for config UI
        self.config_options = {
            'duration': [30, 45, 60, 90, 120],
            'spawn_rate': [2.0, 1.5, 1.0, 0.5, 0.3],
            'speed_mult': [0.5, 1.0, 1.5, 2.0, 3.0],
            'direction': ['Down', 'Diagonal', 'Up']
        }

        # State: START, PLAYING, SETTINGS, STORY_CONFIG, GAMEOVER, STAGE_CLEAR
        self.state = 'START'
        self.stage_cleared_msg_timer = 0
        self.clear_timer_start = 0

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

    def reset_game_state(self, restart_stage=False):
        self.score = 0
        self.start_time = time.time()
        self.score_saved = False
        self.fruits = []
        self.effects = [] 
        self.last_spawn_time = time.time()
        
        if self.current_mode == self.MODE_FREE:
            self.game_duration = self.free_settings['duration']['options'][self.free_settings['duration']['idx']]
            self.spawn_interval = self.free_settings['spawn_rate']['options'][self.free_settings['spawn_rate']['idx']]
            speed_val = self.free_settings['speed_mult']['options'][self.free_settings['speed_mult']['idx']]
            dir_val = self.free_settings['direction']['options'][self.free_settings['direction']['idx']]
        else: # STORY
            if not restart_stage:
                # current_stage should be managed by the clear logic, 
                # but if we are just starting (from START screen), it should be 0.
                # If we are restarting a stage, current_stage is already set.
                pass
                
            cfg = self.story_config[self.current_stage]
            self.game_duration = cfg['duration']
            self.spawn_interval = cfg['spawn_rate']
            speed_val = cfg['speed_mult']
            dir_val = cfg['direction']

        self.current_speed_mult = speed_val
        self.current_direction = dir_val

        # Theoretical Max Score for Clear Condition (Head capture = 3 pts)
        # Max Drops = Duration / Interval
        # Max Score = Max Drops * 3
        if self.spawn_interval > 0:
            total_drops = self.game_duration / self.spawn_interval
            self.target_score = int(total_drops * 3 * 0.60) # 60% requirement
        else:
            self.target_score = 9999

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
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'mode': self.current_mode,
            'stage': self.current_stage + 1 if self.current_mode == self.MODE_STORY else '-'
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
        self.fruits.append(Fruit(self.width, self.height, self.images, self.current_speed_mult, self.current_direction))

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
        
        cv2.putText(image, "BODY CATCH GAME", (self.width//2 - 300, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 0), 5)

        mode_str = f"MODE: {self.current_mode}"
        mode_color = (0, 255, 255) if self.current_mode == self.MODE_FREE else (255, 0, 255)
        cv2.putText(image, mode_str, (self.width//2 - 150, 250), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, mode_color, 3)

        cv2.putText(image, "Press 'M' to Toggle Mode", (self.width//2 - 150, 300), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)
        
        cv2.putText(image, "Press 'S' to START", (self.width//2 - 200, 400), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
        
        settings_text = "Press 'P' for FREE SETTINGS" if self.current_mode == self.MODE_FREE else "Press 'P' to EDIT STAGES"
        cv2.putText(image, settings_text, (self.width//2 - 250, 500), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        
        cv2.putText(image, "Press 'Q' or ESC to Quit", (self.width//2 - 200, 600), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2)

    def draw_settings_screen(self, image):
        cv2.rectangle(image, (0, 0), (self.width, self.height), (20, 20, 20), -1)
        
        cv2.putText(image, "FREE MODE SETTINGS", (self.width//2 - 250, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4)

        y_off = 200
        keys = list(self.free_settings.keys())
        
        for idx, key in enumerate(keys):
            item = self.free_settings[key]
            val = item['options'][item['idx']]
            label = item['label']
            
            text = f"{idx+1}. {label}: {val}"
            cv2.putText(image, text, (self.width//2 - 300, y_off), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)
            y_off += 80

        cv2.putText(image, "Press 1-4 to Change | 'B' Back", (self.width//2 - 300, 600), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)

    def draw_story_config_screen(self, image):
        cv2.rectangle(image, (0, 0), (self.width, self.height), (30, 0, 30), -1)
        
        cv2.putText(image, "STORY LEVEL EDITOR", (self.width//2 - 300, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 0, 255), 4)

        # Stage Selector
        cv2.putText(image, f"< Stage {self.current_stage + 1} >", (self.width//2 - 150, 160), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)
        cv2.putText(image, "(Use ',' and '.' to Change Stage)", (self.width//2 - 200, 190), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Configs for current stage
        cfg = self.story_config[self.current_stage]
        y_off = 250
        
        # 1. Duration
        txt = f"1. Duration: {cfg['duration']}s"
        cv2.putText(image, txt, (self.width//2 - 300, y_off), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        y_off += 60

        # 2. Spawn Rate
        txt = f"2. Spawn Rate: {cfg['spawn_rate']}s"
        cv2.putText(image, txt, (self.width//2 - 300, y_off), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        y_off += 60

        # 3. Speed
        txt = f"3. Speed Mult: x{cfg['speed_mult']}"
        cv2.putText(image, txt, (self.width//2 - 300, y_off), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        y_off += 60

        # 4. Direction
        txt = f"4. Direction: {cfg['direction']}"
        cv2.putText(image, txt, (self.width//2 - 300, y_off), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        y_off += 60

        cv2.putText(image, "Press 1-4 to Cycle Options", (self.width//2 - 300, 600), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)
        cv2.putText(image, "Press 'B' to Back", (self.width//2 - 300, 650), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)

    def draw_ui(self, image):
        # Score & Time
        cv2.putText(image, f"Score: {self.score}", (30, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        elapsed_time = time.time() - self.start_time
        remaining_time = max(0, self.game_duration - int(elapsed_time))
        color = (255, 255, 255)
        if remaining_time <= 10:
            color = (0, 0, 255) 
        
        cv2.putText(image, f"Time: {remaining_time}", (30, 140), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)

        if self.current_mode == self.MODE_STORY:
             cv2.putText(image, f"Stage: {self.current_stage + 1}/5", (30, 200), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 255), 2)
             cv2.putText(image, f"Target: {self.target_score}", (30, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)

        if remaining_time == 0:
            self.check_game_over()

    def check_game_over(self):
        if self.current_mode == self.MODE_FREE:
            self.state = 'GAMEOVER'
            if not self.score_saved:
                self.save_high_score()
        else: # STORY
            if self.score >= self.target_score:
                # CLEAR
                if self.current_stage < 4:
                    self.current_stage += 1
                    self.state = 'STAGE_CLEAR'
                    self.clear_timer_start = time.time()
                else:
                    # All Stages Cleared
                    self.state = 'GAMEOVER'
                    self.save_high_score()
            else:
                # FAILED
                self.state = 'GAMEOVER'

    def draw_game_over(self, image):
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, image, 0.15, 0, image)

        title = "GAME OVER"
        color = (0, 0, 255)
        
        if self.current_mode == self.MODE_STORY:
            if self.score >= self.target_score and self.current_stage == 4:
                title = "ALL STAGES CLEARED!"
                color = (0, 255, 0)
            elif self.score < self.target_score:
                title = "STAGE FAILED..."

        cv2.putText(image, title, (self.width//2 - 250, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, color, 5)
        
        cv2.putText(image, f"Final Score: {self.score}", (self.width//2 - 150, 180), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        if self.current_mode == self.MODE_STORY:
             cv2.putText(image, f"Target Was: {self.target_score}", (self.width//2 - 150, 220), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)

        # High Scores
        cv2.putText(image, "Top 10 High Scores:", (self.width//2 - 250, 280), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 215, 0), 2)
        
        y_offset = 320
        for idx, entry in enumerate(self.high_scores):
            stg = f"S{entry['stage']}" if 'stage' in entry and entry['stage'] != '-' else ""
            mode_lbl = entry.get('mode', 'FREE')[:1] # F or S
            score_str = f"{idx+1}. [{mode_lbl}{stg}] {entry['score']} - {entry['time']}"
            cv2.putText(image, score_str, (self.width//2 - 350, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            y_offset += 25

        help_text1 = "Press 'R' to Restart"
        help_text2 = "Press 'P' for Settings"
        help_text3 = "Press 'Q' or ESC to Quit"
        
        cv2.putText(image, help_text1, (self.width//2 - 200, 600), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(image, help_text2, (self.width//2 - 200, 640), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(image, help_text3, (self.width//2 - 200, 680), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2)

    def draw_stage_clear(self, image):
        cv2.rectangle(image, (0, 0), (self.width, self.height), (0, 50, 0), -1)
        cv2.putText(image, f"STAGE {self.current_stage} CLEARED!", (self.width//2 - 300, 300), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 4)
        cv2.putText(image, "Get Ready for Next Stage...", (self.width//2 - 250, 400), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

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
                    if self.current_mode == self.MODE_STORY:
                        self.current_stage = 0
                    self.reset_game_state(restart_stage=True)
                    self.state = 'PLAYING'
                elif key == ord('p'):
                    if self.current_mode == self.MODE_FREE:
                        self.state = 'SETTINGS'
                    else:
                        self.state = 'STORY_CONFIG'
                elif key == ord('m'):
                    self.current_mode = self.MODE_STORY if self.current_mode == self.MODE_FREE else self.MODE_FREE
                
                self.draw_start_screen(image)

            elif self.state == 'SETTINGS':
                if key == ord('b') or key == ord('p'):
                    self.state = 'START'
                
                keys = list(self.free_settings.keys())
                if key in [ord('1'), ord('2'), ord('3'), ord('4')]:
                    idx = int(chr(key)) - 1
                    if 0 <= idx < len(keys):
                        k = keys[idx]
                        self.free_settings[k]['idx'] = (self.free_settings[k]['idx'] + 1) % len(self.free_settings[k]['options'])
                
                self.draw_settings_screen(image)
            
            elif self.state == 'STORY_CONFIG':
                if key == ord('b') or key == ord('p'):
                    self.state = 'START'
                
                # Navigate Stages: , and .
                if key == ord(','): 
                    self.current_stage = max(0, self.current_stage - 1)
                elif key == ord('.'):
                    self.current_stage = min(4, self.current_stage + 1)
                
                # Modify Config for current stage
                # 1: Duration, 2: Spawn Rate, 3: Speed, 4: Direction
                cfg = self.story_config[self.current_stage]
                opts = self.config_options
                
                if key == ord('1'):
                    curr_idx = opts['duration'].index(cfg['duration'])
                    cfg['duration'] = opts['duration'][(curr_idx + 1) % len(opts['duration'])]
                elif key == ord('2'):
                    curr_idx = opts['spawn_rate'].index(cfg['spawn_rate'])
                    cfg['spawn_rate'] = opts['spawn_rate'][(curr_idx + 1) % len(opts['spawn_rate'])]
                elif key == ord('3'):
                    curr_idx = opts['speed_mult'].index(cfg['speed_mult'])
                    cfg['speed_mult'] = opts['speed_mult'][(curr_idx + 1) % len(opts['speed_mult'])]
                elif key == ord('4'):
                    curr_idx = opts['direction'].index(cfg['direction'])
                    cfg['direction'] = opts['direction'][(curr_idx + 1) % len(opts['direction'])]

                self.draw_story_config_screen(image)

            elif self.state == 'PLAYING':
                if key == ord('r'): # Restart mid-game
                    self.reset_game_state(restart_stage=True)

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

            elif self.state == 'STAGE_CLEAR':
                if time.time() - self.clear_timer_start > 3.0: # Show for 3 seconds
                    self.reset_game_state()
                    self.state = 'PLAYING'
                self.draw_stage_clear(image)

            elif self.state == 'GAMEOVER':
                if key == ord('r'):
                    if self.current_mode == self.MODE_STORY:
                         if self.score >= self.target_score and self.current_stage == 4:
                            self.current_stage = 0
                         self.reset_game_state(restart_stage=True)
                    else:
                        self.reset_game_state()
                    self.state = 'PLAYING'
                elif key == ord('p'):
                    self.state = 'SETTINGS' if self.current_mode == self.MODE_FREE else 'STORY_CONFIG'
                
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
