import cv2
from pathlib import Path
from PIL import Image, ImageTk
import customtkinter as ctk
import time

class VideoPlayer(ctk.CTkCanvas):
    def __init__(self, app, video_path = ""):
        super().__init__(app, bg="black")
        self.on_frame_update = None     # a callback function for when the current frame changes
        self.playing         = False    # whether video is playing or not
        self.play_button     = None     # play / pause button
        self.slider          = None     # slider for seeking
        self.seek_job        = None     # handle for the debounced callback
        self.last_seek       = 0.0      # timestamp of the last actual seek
        self.min_seek_ms     = 180      # throttle
        self.debounce_ms     = 200      # debounce
        if video_path: self.set_video(video_path)
        
    def set_video(self, video_path: str, slider = None, slider_row = 0, slider_col = 0, slider_pad = 0):
        # Video setup
        self.cap = cv2.VideoCapture(str(video_path))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.delay = int(1000 / self.fps)
        self.current_frame_index = 0
        
        self.image_id = self.create_image(0, 0, anchor="nw")
        self.photo = None  # keep reference
        
        # Seek slider
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if slider:
            self.slider = slider
            slider.configure(
                from_=0,
                to=self.total_frames,
                number_of_steps=self.total_frames,
                command=self.on_seek
            )
            slider.grid(
                row=slider_row,
                column=slider_col,
                padx=slider_pad,
                pady=slider_pad,
                sticky="ew"
            )
            slider.set(0)
            self.on_seek(0)
        
    def _schedule_next(self):
        now = time.perf_counter()
        self.next_frame_time += 1.0 / self.fps  # time of next frame
        delay_ms = max(0, (self.next_frame_time - now) * 1000)
        self.after(int(delay_ms), self._next_frame)
        
    def play_pause(self):
        if self.playing:
            self.pause()
        else:
            self.play()
        
    def play(self):
        self.playing = True
        if self.play_button:
            self.play_button.configure(text="Pause")
        if self.current_frame_index >= self.total_frames:
            self.current_frame_index = 0
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        self.next_frame_time = time.perf_counter()
        self._next_frame()
    
    def pause(self):
        self.playing = False
        if self.play_button: self.play_button.configure(text="Play")
    
    def on_seek(self, value):
        # slider callback gives float; convert to int
        idx = int(float(value))
        now = time.perf_counter() * 1000  # ms

        # throttle; if enough time has passed since last seek then seek immediately
        if now - self.last_seek >= self.min_seek_ms:
            self._perform_seek(idx)
            self.last_seek = now

        # debounce; cancel any pending final seek, schedule a fresh one
        if self.seek_job is not None:
            self.after_cancel(self.seek_job)

        self.seek_job = self.after(self.debounce_ms, 
                                lambda: self._perform_seek(idx))
    
    def _perform_seek(self, frame_index):
        # Pause playback during seek
        was_playing = self.playing
        self.pause()

        # Seek in the video
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        self.current_frame_index = frame_index
        if self.slider: self.slider.set(frame_index)
        self._show_frame()

        # Restore playback if it was playing
        if was_playing:
            self.play()
    
    def _next_frame(self):
        if not self.playing:
            return
        ret, frame = self.cap.read()
        self.current_frame_index += 1
        if not ret:
            self.playing = False
            if self.play_button: self.play_button.configure(text="Play")
            return  # end of video
        if self.slider: self.slider.set(self.current_frame_index)
        self._show_frame(frame)
        self._schedule_next()
        # self.after(self.delay, self._next_frame)
    
    def _show_frame(self, frame=None):
        # If frame not provided, re‐grab current frame
        if frame is None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_index)
            ret, frame = self.cap.read()
            if not ret:
                return
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cw, ch = self.winfo_width(), self.winfo_height()
        h, w = frame.shape[:2]
        scale = min(cw/w, ch/h)
        new_w, new_h = int(w*scale), int(h*scale)
        nw, nh = int(w*scale), int(h*scale)
        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        img = Image.fromarray(frame)
        
        # Center
        x = (cw - new_w)//2
        y = (ch - new_h)//2
        
        self.photo = ImageTk.PhotoImage(img)
        self.itemconfig(self.image_id, image=self.photo)
        self.coords(self.image_id, x, y)
        
        if self.on_frame_update: self.on_frame_update(self.current_frame_index, self.fps)
        