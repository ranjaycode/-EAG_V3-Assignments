import threading
import time
import cv2
import numpy as np
import pyautogui
from pathlib import Path

class ScreenRecorder(threading.Thread):
    def __init__(self, output_path: Path, fps: int = 5):
        super().__init__()
        self.output_path = output_path
        self.fps = fps
        self.running = False
        self.daemon = True

    def run(self):
        self.running = True
        screen_size = pyautogui.size()
        # Use MP4V codec for mp4 format
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(self.output_path), fourcc, self.fps, screen_size)
        
        delay = 1.0 / self.fps
        try:
            while self.running:
                start_time = time.time()
                # Capture screen
                img = pyautogui.screenshot()
                # Convert PIL image to BGR numpy array
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                # Write to video
                writer.write(frame)
                
                # Regulate frame rate
                elapsed = time.time() - start_time
                if elapsed < delay:
                    time.sleep(delay - elapsed)
        except Exception as e:
            print(f"[recorder] Error during recording: {e}")
        finally:
            writer.release()

    def stop(self):
        self.running = False
