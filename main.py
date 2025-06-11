from PIL import Image, ImageTk
from util import *
import customtkinter as ctk
from customtkinter import filedialog
from tkinter import messagebox, simpledialog
from convert_video import ffmpeg
import subprocess
from pathlib import Path
from video_player import VideoPlayer
from math import floor, pi, sin, cos, radians, sqrt
import time
from preferences import PreferencesWindow, Preferences
import shutil
from shapes import *

basedir = Path(__file__).resolve().parent

log(f"Checking for dtm2text in PATH")
if not shutil.which("dtm2text"):
    err_popup("dtm2text not found either in PATH or your VENV. Install requirements with:\n" \
        "pip install -r requirements.txt")
    exit()

corner_radius = cr = 6
padding = pd = 4 

settings = Preferences()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.dtm = ""
        self.dtm_inputs = []
        self.vid = ""
        # timers used for fade effect
        self.button_timers = [0.0] *  10
        # list of button draw objects to iterate through when being pressed/fading
        self.button_draws = []
        # global button draw objects
        self.drw_left_stick = None
        self.drw_c_stick = None
        self.drw_l_btn = None
        self.drw_r_btn = None
        
        self.title("DTM Visualiser")
        # center window on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 1100
        window_height = 600
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # setup a grid layout
        self.grid_columnconfigure(0, weight=0) # for the sidebar
        self.grid_columnconfigure(1, weight=1) # for canvas which is resizable
        self.grid_columnconfigure(2, weight=0) # for gamecube controller, showing inputs
        # self.grid_columnconfigure(2, weight=0) # for canvas which is resizable
        self.grid_rowconfigure(0, weight=1) # for the top row (sidebar + canvas)
        self.grid_rowconfigure(1, weight=0) # for the video player slider
        self.grid_rowconfigure(2, weight=0) # for the statusbar

        # left-most column
        sidebar = ctk.CTkFrame(self)
        sidebar.grid(row=0, rowspan=2, column=0, padx=pd, pady=pd, sticky="ns")
        sidebar.grid_rowconfigure(0, weight=1)
        sidebar.grid_rowconfigure(1, weight=0)

        sidebar_upper = ctk.CTkFrame(sidebar, fg_color="transparent")
        sidebar_upper.grid(row=0, column=0, padx=0, pady=pd, sticky="nw")

        # bottom status bar for loaded labels
        statusbar = ctk.CTkFrame(self)
        statusbar.grid(row=2, column=0, columnspan=2, padx=pd, pady=pd, sticky="ew")

        # canvas for painting the video and elements on top
        self.video_player = VideoPlayer(self)
        self.video_player.grid(row=0, column=1, padx=pd, pady=pd, sticky="nsew")

        # gamecube controller for displaying inputs
        pil_img = Image.open(basedir / "images" / "gc.png")
        target_width = 300
        aspect_ratio = target_width / pil_img.width

        self.img = ImageTk.PhotoImage(pil_img.resize((target_width, round(pil_img.height * aspect_ratio))))

        self.img_gc = ctk.CTkCanvas(
            self,
            width=self.img.width(),
            height=self.img.height(),
            highlightthickness=0,
            bg=self.cget("fg_color")[1]
        )
        self.img_gc.grid(row=0, column=2, sticky="nw")
        self.img_gc.create_image(0, 0, anchor="nw", image=self.img)
        self.init_draws()

        # labels
        self.lbl_dtm = ctk.CTkLabel(statusbar, text=self.get_dtm_text(), font=ctk.CTkFont(size=14))
        self.lbl_dtm.grid(row=0, column=0, sticky="w", padx=pd, pady=0)
        self.lbl_vid = ctk.CTkLabel(statusbar, text=self.get_vid_text(), font=ctk.CTkFont(size=14))
        self.lbl_vid.grid(row=1, column=0, sticky="w", padx=pd, pady=0)

        # buttons
        self.btn_sample = ctk.CTkButton(sidebar_upper, text="Load Sample", command=self.load_sample, corner_radius=cr)
        self.btn_sample.grid(row=0, column=0, padx=pd, pady=(0, pd))
        self.btn_dtm = ctk.CTkButton(sidebar_upper, text="Load DTM", command=self.load_dtm, corner_radius=cr)
        self.btn_dtm.grid(row=1, column=0, padx=pd, pady=pd)
        self.btn_video = ctk.CTkButton(sidebar_upper, text="Load Video", command=self.load_video, corner_radius=cr)
        self.btn_video.grid(row=2, column=0, padx=pd, pady=pd)
        self.btn_unload = ctk.CTkButton(sidebar_upper, text="Unload", command=self.unload, corner_radius=cr)
        self.btn_unload.grid(row=3, column=0, padx=pd, pady=pd)
        # self.spacer
        self.spacer = ctk.CTkFrame(sidebar_upper, height=20, width=1)
        self.spacer.grid(row=4, column=0, padx=pd, pady=pd)
        # preferences
        self.btn_pref = ctk.CTkButton(sidebar_upper, text="Preferences", command=self.open_pref, corner_radius=cr)
        self.btn_pref.grid(row=5, column=0, padx=pd, pady=pd)
        # lower pane
        self.btn_play = ctk.CTkButton(sidebar, text="Play", command=self.play_video, corner_radius=cr)
        self.btn_play.grid(row=1, column=0, padx=pd, pady=pd)
        self.video_player.play_button = self.btn_play
        self.video_player.on_frame_update = self.draw_inputs

        # keyboard shortcuts
        self.bind("<space>", self.play_video)
        self.bind("<k>", self.play_video)
        self.bind("<Left>", self.try_seek)
        self.bind("<j>", self.try_seek)
        self.bind("<Right>", self.try_seek)
        self.bind("<l>", self.try_seek)

        # playback slider
        self.slider = ctk.CTkSlider(self)

    def get_dtm_text(self) -> str:
        if len(self.dtm) > 0:
            return f"DTM loaded: {self.dtm}"
        else:
            return "DTM not loaded"
        
    def get_vid_text(self) -> str:
        if len(self.vid) > 0:
            return f"Video loaded: {self.vid}"
        else:
            return "Video not loaded"
        
    def set_dtm(self, filename: str):
        # if the dtm file is an empty string, then unload
        if len(filename) == 0:
            log("Unloading DTM file")
            self.dtm = ""
            self.lbl_dtm.configure(text=self.get_dtm_text())
            return
        
        file = Path(filename)
        if not file.exists():
            err_popup(f"DTM file was not found:\n\n{file.absolute()}")
            return
        
        # check if the output dtm file already exists and if so try to remove it
        output_dir = basedir / "dtm2text"
        output_dir.mkdir(exist_ok=True)
        output_fn = output_dir / f"{file.name}_inputs.txt"
        if output_fn.exists() and output_fn.is_file():
            try:
                output_fn.unlink()
                log(f"Removed existing DTM file: {output_fn.absolute()}")
            except Exception as e:
                err_popup(f"Failed to replace existing DTM inputs file:\n\n{e}")
                return
            
        log(f"Converting DTM file to text at: {file.absolute()}")
        subprocess.run(
            [
                "dtm2text",
                str(file.absolute()),
                "--no-header",
                "-o", str(output_dir.absolute())
            ],
            cwd=output_dir.absolute()
        )
        
        # if dtm2text fails there won't be an output file and thus we can't set the new dtm
        if not output_fn.exists():
            err_popup(f"Failed to convert DTM file to TXT.\nOutput not found at:\n\n{output_fn}")
            return
        
        log("Successful conversion of DTM to TXT")
        
        with open(output_fn, 'r') as f:
            self.dtm_inputs = [line.strip() for line in f.readlines()]
        log("Read DTM input lines")
        
        self.dtm = str(file.absolute())
        self.lbl_dtm.configure(text=self.get_dtm_text())
        
    def set_vid(self, filename: str, compression: str = "Ask"):
        # if the video file is an empty string, then unload
        if len(filename) == 0:
            log("Unloading video file")
            self.vid = ""
            self.lbl_vid.configure(text=self.get_vid_text())
            return
        
        file = Path(filename)
        if not file.exists():
            err_popup(f"Video file was not found:\n\n{filename}")
            return
        
        if not compression == "Never":
            # init compression as true, assuming compression is set to always
            result = True
            # ask if the user wants to compress the video using FFmpeg, if compression is set to ask
            if compression == "Ask": result = messagebox.askyesnocancel(
                "Compress Video",
                "Do you want to compress this video to 480p using FFmpeg?\n\n" \
                "NOTE: This requires you to have FFmpeg installed and added to PATH.\n" \
                "Compressed videos are saved in the ./videos/ directory.\n\n" \
                "You will also need to know what framerate your game was running at.\n" \
                "Generally this is 30fps for NTSC and 25fps for PAL."
            )
            if result == True: # pressed Yes
                fps = "a"
                # check if the user has a default compression fps set
                if compression == "Always" and "compress_video_fps" in settings.options.keys():
                    fps = settings.options["compress_video_fps"].value
                # initial message
                message = "What was the game's framerate when recording?\n\n" \
                    "Generally, NTSC games run at 30fps, PAL games run at 25fps."
                while not fps.isdigit():
                    # i know I could just do askinteger() but then i cant loop to ask again when
                    # the input is invalid as both cancelling and invalid input returns None.
                    # with a string, i can determine cancelled vs invalid input
                    fps = simpledialog.askstring(
                        "Video FPS",
                        message
                    )
                    if not fps:
                        log("Video compression cancelled by user when asked for FPS")
                        return
                    if not fps.isdigit():
                        # new message after an incorrect input
                        message = "Enter the frames per second as a number for the compressed video."
                
                log(f"User inputted video FPS: {fps}")
                
                # validate videos folder
                videos = basedir / "videos"
                videos.mkdir(exist_ok=True)
                # get pre-determined output file name
                output_fn = basedir / "videos" / f"{file.stem}.mp4"
                # check if compressed file already exists, and if so, asks the user if they want to
                # overwrite it or cancel the operation entirely
                if output_fn.exists():
                    if not messagebox.askokcancel(
                        "Overwrite Video",
                        "It looks like this video or a video with a similar filename has already been " \
                        "compressed inside ./videos/\n\n" \
                        "Continuing will overwrite the file, would you like to continue?"
                    ):
                        log("Video loading and compression cancelled by user to avoid overwriting")
                        return
                    else:
                        # attempts to remove the existing file, and cancels if it fails
                        log("Attempting to remove original file...")
                        try:
                            output_fn.unlink()
                            log(f"Removed existing video file: {output_fn.absolute()}")
                        except Exception as e:
                            err_popup(f"Failed to replace existing video file:\n\n{e}")
                            return
                
                # calls ffmpeg with pre-defined command for a small 480p30 mp4 video
                if ffmpeg(
                    input=str(file.absolute()),
                    output=str(output_fn.absolute()),
                    fps=fps
                ):
                    file = output_fn
            
            elif result is None: # pressed Cancel
                log("User cancelled video load when prompted about video compression")
                return
            
            else: # pressed No
                log("User declined video compression, continuing with existing video")
                
        else: # skip_compression == False
            log("Video compression automatically skipped")
        
        # load video to canvas
        try:
            self.video_player.set_video(file.absolute(), self.slider, 1, 1, pd)
        except Exception as e:
            err_popup(f"Failed to load the video to canvas using cv2:\n\n{e}")
            return
        
        log(f"Loaded video at: {file.absolute()}")
        self.vid = str(file.absolute())
        self.lbl_vid.configure(text=self.get_vid_text())

    # button callbacks
    def load_sample(self):
        self.set_dtm("sample/pikmin.dtm")
        self.set_vid("sample/pikmin.mp4", compression="Never")
        
    def load_dtm(self):
        # file dialog for selecting only DTM files
        filename = filedialog.askopenfilename(
            filetypes=[(
                "DTM Dolphin Test Movie Files",
                "*.dtm"
            )]
        )
        if filename:
            log(f"Attempting to load DTM at: {filename}")
            self.set_dtm(filename)
        
        # filename will be blank if the user cancels
        else:
            log("User cancelled loading DTM")
        
    def load_video(self):
        # file dialog for selecting specific video files
        filename = filedialog.askopenfilename(
            filetypes=[(
                "Video Files",
                "*.mp4;*.avi;*.mov"
            )]
        )
        if filename:
            log(f"Attempting to load video at: {filename}")
            self.set_vid(filename, settings.options["compress_video"].value)
        
        # filename will be blank if the user cancels
        else:
            log("User cancelled loading video")

    def play_video(self, event = None):
        if not self.dtm or not self.vid:
            err("Both a DTM file and a video must be loaded for playback")
            return
        
        # play function handles if its already playing or not
        self.video_player.play_pause()

    def try_seek(self, event = None, value = 50):
        if event.keysym == "Left" or event.keysym == "j":
            self.slider.set(max(self.slider.get() - 50, 0))
        elif event.keysym == "Right" or event.keysym == "l":
            self.slider.set(min(self.slider.get() + 50, self.slider.cget("to")))
        self.video_player.on_seek(self.slider.get())

    # removes any currently loaded videos from the dtm and vid variables, pauses video if playing
    # TODO: implement clear image function in VideoPlayer and call that here
    def unload(self):
        self.set_dtm("")
        self.set_vid("")
        if self.video_player.playing:
            self.video_player.pause()
        # clear canvas
        self.video_player.delete("all")
        # reset controller
        self.draw_inputs(0, True)
        self.slider.grid_forget()

    def open_pref(self):
        PreferencesWindow(self, settings)

    def init_draws(self):
        # sticks
        self.drw_left_stick = self.img_gc.create_oval(
            28+10, 51+10, 28+44, 51+44,
            fill="#cccccc",
            outline="black",
            width=1
        )
        self.drw_c_stick = self.img_gc.create_oval(
            174+14, 122+14, 174+52-14, 122+52-14,
            fill="#ffff00",
            outline="black",
            width=1
        )
        # buttons
        drw_start_btn = self.img_gc.create_oval(
            143, 73, 143+15, 73+15,
            fill="#333333",
            outline="black",
            width=1
        )
        drw_a_btn = self.img_gc.create_oval(
            226, 60, 226+36, 60+36,
            fill="#333333",
            outline="black",
            width=1
        )
        drw_b_btn = self.img_gc.create_oval(
            200, 85, 200+23, 85+23,
            fill="#333333",
            outline="black",
            width=1
        )
        # beans (X, Y)
        x, y = 280, 70
        w, h = 16, 32
        drw_x_btn = create_bean_shape(
            self.img_gc,
            x, y, w, h,
            rotation_deg=165,
            fill="#333333",
            outline="black",
            width=1
        )
        x, y = 237, 44
        w, h = 32, 16
        drw_y_btn = create_bean_shape(
            self.img_gc,
            x, y, h, w,
            rotation_deg=75,
            fill="#333333",
            outline="black",
            width=1
        )
        # bumpers (L, R, Z)
        x, y = 50, 22
        w, h = 46, 28
        self.drw_l_btn = create_semi_circle(
            self.img_gc,
            x, y, w, h,
            rotation_deg=157,
            direction="top",
            fill="#333333",
            outline="black",
            width=1
        )
        x, y = 246, 22
        w, h = 46, 28
        self.drw_r_btn = create_semi_circle(
            self.img_gc,
            x, y, w, h,
            rotation_deg=203,
            direction="top",
            fill="#333333",
            outline="black",
            width=1
        )
        x, y = 246, 22
        w, h = 54, 12
        drw_z_btn = create_semi_circle(
            self.img_gc,
            x, y, w, h,
            rotation_deg=203,
            direction="top",
            fill="#333333",
            outline="black",
            width=1
        )
        # D-PAD arrows (UP DOWN LEFT RIGHT)
        x, y = 99, 134
        w = 9
        drw_du_btn = create_triangle(
            self.img_gc,
            x, y, w,
            rotation_deg=0,
            fill="#cccccc"
        )
        x, y = 99, 162
        drw_dd_btn = create_triangle(
            self.img_gc,
            x, y, w,
            rotation_deg=180,
            fill="#cccccc"
        )
        x, y = 85, 148
        drw_dl_btn = create_triangle(
            self.img_gc,
            x, y, w,
            rotation_deg=270,
            fill="#cccccc"
        )
        x, y = 113, 148
        drw_dr_btn = create_triangle(
            self.img_gc,
            x, y, w,
            rotation_deg=90,
            fill="#cccccc"
        )
        
        self.button_draws.append(drw_start_btn)
        self.button_draws.append(drw_a_btn)
        self.button_draws.append(drw_b_btn)
        self.button_draws.append(drw_x_btn)
        self.button_draws.append(drw_y_btn)
        self.button_draws.append(drw_z_btn)
        # note that L and R are excluded from this list because i draw their fill
        # based on how hard they are pressed (analog triggers)
        self.button_draws.append(drw_du_btn)
        self.button_draws.append(drw_dd_btn)
        self.button_draws.append(drw_dl_btn)
        self.button_draws.append(drw_dr_btn)

    def draw_inputs(self, frame_index, draw_blank=False):
        # default frame inputs
        frame_inputs = "0:0:0:0:0:0:0:0:0:0:0:0:0:0:128:128:128:128"
        # exit if no DTM loaded
        if not draw_blank:
            if not self.dtm or len(self.dtm_inputs) == 0:
                print("no dtm")
                return
            
            # get frame inputs from dtm
            if frame_index <= len(self.dtm_inputs):
                frame_inputs = self.dtm_inputs[floor((frame_index - 1) * 4)]
        
        # get btn presses and stick values
        btn = [int(i) for i in frame_inputs.split(":")]
        mainx: int = btn[14]
        mainz: int = btn[15]
        cx:    int = btn[16]
        cz:    int = btn[17]
        l:     int = btn[12]
        r:     int = btn[13]
        
        # position the main left stick, note that 0, 0 is top-left and 256, 256 is bottom-right
        x, y = (28, 51)
        x += round(10 * (mainx - 128) / 128)
        y -= round(10 * (mainz - 128) / 128)
        w, h = (x + 54, y + 54)
        stick_rect = (x+10, y+10, w-10, h-10)
        self.img_gc.coords(self.drw_left_stick, stick_rect)
        
        # position the c stick, same as above
        x, y = (174, 122)
        x += round(10 * (cx - 128) / 128)
        y -= round(10 * (cz - 128) / 128)
        w, h = (x + 52, y + 52)
        stick_rect = (x+14, y+14, w-14, h-14)
        self.img_gc.coords(self.drw_c_stick, stick_rect)
        
        # main buttons (Start,      A,          B,          X, Y,               Z        DPAD UDLR)
        btn_colours = ["#b3b3b3", "#00ffff", "#ff0000"] + ["#cccccc"] * 2 + ["#0000c0"] + ["#808080"] * 4
        end_rgb = ["#333333"] * 6 + ["#cccccc"] * 4
        fade_duration = 0.6
        for i, drw_btn in enumerate(self.button_draws):
            start_rgb = hex_to_rgb(btn_colours[i])
            # if button is just pressed, update timer to now
            if btn[i]: self.button_timers[i] = time.time()
            # gets duration since last press for fade progress
            dif = time.time() - self.button_timers[i]
            if dif <= fade_duration:
                eased_t = ease_out_expo(dif / fade_duration) # looks nicer than linear
                # calculates the rgb colour between start and end colour then converts it to hex
                fill = rgb_to_hex(tuple(
                    int(start + (end - start) * eased_t)
                    for start, end in zip(start_rgb, hex_to_rgb(end_rgb[i]))
                ))
                self.img_gc.itemconfig(drw_btn, fill=fill) # update colour
        
        # L and R triggers (analog demonstration based on how hard their pressed)
        # the sample video uses a controller without analog triggers so this effect isn't obvious
        start_rgb = hex_to_rgb(btn_colours[0])
        eased_t = 1.0 - ease_out_expo(l / 255) # inverted for fading IN instead of OUT
        # calculates the rgb colour between start and end colour then converts it to hex
        fill = rgb_to_hex(tuple(
            int(start + (end - start) * eased_t)
            for start, end in zip(start_rgb, hex_to_rgb(end_rgb[0]))
        ))
        self.img_gc.itemconfig(self.drw_l_btn, fill=fill)
        
        # R trigger
        eased_t = 1.0 - ease_out_expo(r / 255)
        fill = rgb_to_hex(tuple(
            int(start + (end - start) * eased_t)
            for start, end in zip(start_rgb, hex_to_rgb(end_rgb[0]))
        ))
        self.img_gc.itemconfig(self.drw_r_btn, fill=fill)

# set custom tkinter appearance and theme
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("themes/lavender.json")

# initialise ctk window title
app = App()

bring_window_to_front() # on macOS if pyobjc is installed
app.mainloop()
