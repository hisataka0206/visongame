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
    def __init__(self, screen_width, images=None):
        self.type = random.choice(['banana', 'orange'])
        self.x = random.randint(50, screen_width - 50)
        self.y = 0
        self.speed = random.uniform(5, 10) # Pixels per frame
        self.radius = 30
        self.images = images
        
        if self.type == 'banana':
            self.color = (0, 255, 255) # Yellow
        else:
            self.color = (0, 165, 255) # Orange

    def update(self):
        self.y += self.speed

    def draw(self, image):
        img_to_draw = None
        if self.images and self.type in self.images:
            img_to_draw = self.images[self.type]

        if img_to_draw is not None:
            # Overlay image with alpha channel
            h, w, _ = img_to_draw.shape
            x_pos = int(self.x - w // 2)
            y_pos = int(self.y - h // 2)
            
            # Boundary checks to prevent crash if fruit is partially off-screen
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
            # Fallback to circle
            cv2.circle(image, (int(self.x), int(self.y)), self.radius, self.color, -1)
            # Add a border for visibility
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

        # Game State
        self.reset_game_state()
        
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

    def reset_game_state(self):
        self.score = 0
        self.start_time = time.time()
        self.game_duration = 60
        self.game_over = False
        self.score_saved = False # Flag to prevent multiple saves
        
        self.fruits = []
        self.effects = [] 
        self.last_spawn_time = time.time()
        self.spawn_interval = 1.0 

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
        # Sort by score descending
        self.high_scores.sort(key=lambda x: x['score'], reverse=True)
        # Keep top 10
        self.high_scores = self.high_scores[:10]
        
        try:
            with open('highscores.json', 'w') as f:
                json.dump(self.high_scores, f, indent=4)
        except Exception as e:
            print(f"Error saving high scores: {e}")
        
        self.score_saved = True

    def spawn_fruit(self):
        self.fruits.append(Fruit(self.width, self.images))

    def detect_collision(self, x, y, points_value):
        caught_indices = []
        for i, fruit in enumerate(self.fruits):
            distance = math.sqrt((x - fruit.x)**2 + (y - fruit.y)**2)
            if distance < 50 + fruit.radius: # Threshold + fruit radius for easier catching
                caught_indices.append(i)
                self.score += points_value
                self.effects.append([fruit.x, fruit.y, 10, 50]) # Start effect
        
        # Remove caught fruits (in reverse order to maintain indices)
        for i in sorted(caught_indices, reverse=True):
            del self.fruits[i]

    def draw_ui(self, image):
        # Score
        cv2.putText(image, f"Score: {self.score}", (30, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        # Time
        elapsed_time = time.time() - self.start_time
        remaining_time = max(0, self.game_duration - int(elapsed_time))
        color = (255, 255, 255)
        if remaining_time <= 10:
            color = (0, 0, 255) # Red warning
        
        cv2.putText(image, f"Time: {remaining_time}", (30, 140), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)

        if remaining_time == 0:
            self.game_over = True
            if not self.score_saved:
                self.save_high_score()

    def draw_game_over(self, image):
        # Semi-transparent overlay
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, image, 0.2, 0, image) # Darker overlay for readability

        # Title
        cv2.putText(image, "GAME OVER", (self.width//2 - 200, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 5)
        
        # Final Score
        cv2.putText(image, f"Final Score: {self.score}", (self.width//2 - 150, 180), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        # High Scores List
        cv2.putText(image, "Top 10 High Scores:", (self.width//2 - 250, 250), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 215, 0), 2)
        
        y_offset = 290
        for idx, entry in enumerate(self.high_scores):
            score_str = f"{idx+1}. {entry['score']} pts - {entry['time']}"
            cv2.putText(image, score_str, (self.width//2 - 250, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            y_offset += 30

        # Restart Instruction
        quit_text = "Press 'r' to Restart, 'q' or ESC to Quit"
        quit_size = cv2.getTextSize(quit_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        quit_x = (self.width - quit_size[0]) // 2
        quit_y = self.height - 50
        cv2.putText(image, quit_text, (quit_x, quit_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

    def run(self):
        while self.cap.isOpened():
            success, image = self.cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            # Flip and Convert
            image = cv2.flip(image, 1)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            
            results = self.pose.process(image_rgb)
            image.flags.writeable = True
            
            # Draw landmarks and check collisions if not game over
            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                
                if not self.game_over:
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

            if not self.game_over:
                # Update Fruits/Game Logic
                current_time = time.time()
                if current_time - self.last_spawn_time > self.spawn_interval:
                    self.spawn_fruit()
                    self.last_spawn_time = current_time
                
                for i in range(len(self.fruits) - 1, -1, -1):
                    fruit = self.fruits[i]
                    fruit.update()
                    fruit.draw(image)
                    if fruit.y > self.height:
                        del self.fruits[i]
                
                for i in range(len(self.effects) - 1, -1, -1):
                    ex, ey, r, max_r = self.effects[i]
                    if r < max_r:
                        cv2.circle(image, (int(ex), int(ey)), int(r), (255, 255, 255), 3)
                        self.effects[i][2] += 5 
                    else:
                        del self.effects[i]
                
                self.draw_ui(image)
            else:
                self.draw_game_over(image)

            cv2.imshow('Body Catch Game', image)
            
            key = cv2.waitKey(5) & 0xFF
            if key == 27 or key == ord('q'): # ESC or q
                break
            if key == ord('r'): # Restart
                self.reset_game_state()
        
        # Stop music
        try:
            pygame.mixer.music.stop()
        except:
            pass
            
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = BodyCatchGame()
    game.run()
