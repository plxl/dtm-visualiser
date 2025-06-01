import cv2
from PIL import Image, ImageTk
from util import *
import customtkinter as ctk
from customtkinter import filedialog
from tkinter import messagebox, simpledialog
from convert_video import ffmpeg
import sys
import subprocess
from pathlib import Path
from video_player import VideoPlayer
from math import ceil, floor, pi, sin, cos, radians, sqrt
import time
from preferences import PreferencesWindow, Preferences

basedir = Path(__file__).resolve().parent
dtm2text = basedir / "dtm2text" / "dtm2text.py"

log(f"Checking for dtm2text at: {dtm2text}")
if not dtm2text.exists():
    err_popup("dtm2text not found. Ensure there is 'dtm2text.py' inside the 'dtm2text' folder.\n\n" \
        "If it's not there, pull the latest version from the repository:\n" \
            "https://github.com/plxl/dtm-visualiser")
    exit()

dtm = ""
dtm_inputs = []
vid = ""

corner_radius = cr = 6
padding = pd = 4

settings = Preferences()

def get_dtm_text() -> str:
    if len(dtm) > 0:
        return f"DTM loaded: {dtm}"
    else:
        return "DTM not loaded"
    
def get_vid_text() -> str:
    if len(vid) > 0:
        return f"Video loaded: {vid}"
    else:
        return "Video not loaded"
    
def set_dtm(filename: str):
    global dtm
    
    # if the dtm file is an empty string, then unload
    if len(filename) == 0:
        log("Unloading DTM file")
        dtm = ""
        lbl_dtm.configure(text=get_dtm_text())
        return
    
    file = Path(filename)
    if not file.exists():
        err_popup(f"DTM file was not found:\n\n{file.absolute()}")
        return
    
    # check if the output dtm file already exists and if so try to remove it
    output_dir = dtm2text.parent
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
            sys.executable,
            str(dtm2text.absolute()),
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
    
    global dtm_inputs
    with open(output_fn, 'r') as f:
        dtm_inputs = [line.strip() for line in f.readlines()]
    log("Read DTM input lines")
    
    dtm = str(file.absolute())
    lbl_dtm.configure(text=get_dtm_text())
    
def set_vid(filename: str, compression: str = "Ask"):
    global vid
    
    # if the video file is an empty string, then unload
    if len(filename) == 0:
        log("Unloading video file")
        vid = ""
        lbl_vid.configure(text=get_vid_text())
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
        canvas.set_video(file.absolute(), slider, 1, 1, pd)
    except Exception as e:
        err_popup(f"Failed to load the video to canvas using cv2:\n\n{e}")
        return
    
    log(f"Loaded video at: {file.absolute()}")
    vid = str(file.absolute())
    lbl_vid.configure(text=get_vid_text())

# button callbacks
def load_sample():
    set_dtm("sample/pikmin.dtm")
    set_vid("sample/pikmin.mp4", compression="Never")
    
def load_dtm():
    # file dialog for selecting only DTM files
    filename = filedialog.askopenfilename(
        filetypes=[(
            "DTM Dolphin Test Movie Files",
            "*.dtm"
        )]
    )
    if filename:
        log(f"Attempting to load DTM at: {filename}")
        set_dtm(filename)
    
    # filename will be blank if the user cancels
    else:
        log("User cancelled loading DTM")
    
def load_video():
    # file dialog for selecting specific video files
    filename = filedialog.askopenfilename(
        filetypes=[(
            "Video Files",
            "*.mp4;*.avi;*.mov"
        )]
    )
    if filename:
        log(f"Attempting to load video at: {filename}")
        set_vid(filename, settings.options["compress_video"].value)
    
    # filename will be blank if the user cancels
    else:
        log("User cancelled loading video")

def play_video(event = None):
    if not dtm or not vid:
        err("Both a DTM file and a video must be loaded for playback")
        return
    
    # play function handles if its already playing or not
    canvas.play_pause()

def try_seek(event = None, value = 50):
    if event.keysym == "Left" or event.keysym == "j":
        slider.set(max(slider.get() - 50, 0))
    elif event.keysym == "Right" or event.keysym == "l":
        slider.set(min(slider.get() + 50, slider.cget("to")))
    canvas.on_seek(slider.get())

# removes any currently loaded videos from the dtm and vid variables, pauses video if playing
# TODO: implement clear image function in VideoPlayer and call that here
def unload():
    set_dtm("")
    set_vid("")
    if canvas.playing:
        canvas.pause()
    # clear canvas
    canvas.delete("all")
    slider.grid_forget()

def open_pref():
    PreferencesWindow(app, settings)

# global button draw objects
drw_left_stick = None
drw_c_stick = None
drw_l_btn = None
drw_r_btn = None

def init_draws():
    # sticks
    global drw_left_stick
    drw_left_stick = img_gc.create_oval(
        28+10, 51+10, 28+44, 51+44,
        fill="#cccccc",
        outline="black",
        width=1
    )
    global drw_c_stick
    drw_c_stick = img_gc.create_oval(
        174+14, 122+14, 174+52-14, 122+52-14,
        fill="#ffff00",
        outline="black",
        width=1
    )
    # buttons
    drw_start_btn = img_gc.create_oval(
        143, 73, 143+15, 73+15,
        fill="#333333",
        outline="black",
        width=1
    )
    drw_a_btn = img_gc.create_oval(
        226, 60, 226+36, 60+36,
        fill="#333333",
        outline="black",
        width=1
    )
    drw_b_btn = img_gc.create_oval(
        200, 85, 200+23, 85+23,
        fill="#333333",
        outline="black",
        width=1
    )
    # beans (X, Y)
    x, y = 280, 70
    w, h = 16, 32
    drw_x_btn = create_bean_shape(
        img_gc,
        x, y, w, h,
        rotation_deg=165,
        fill="#333333",
        outline="black",
        width=1
    )
    x, y = 237, 44
    w, h = 32, 16
    drw_y_btn = create_bean_shape(
        img_gc,
        x, y, h, w,
        rotation_deg=75,
        fill="#333333",
        outline="black",
        width=1
    )
    # bumpers (L, R, Z)
    x, y = 50, 22
    w, h = 46, 28
    global drw_l_btn
    drw_l_btn = create_semi_circle(
        img_gc,
        x, y, w, h,
        rotation_deg=157,
        direction="top",
        fill="#333333",
        outline="black",
        width=1
    )
    x, y = 246, 22
    w, h = 46, 28
    global drw_r_btn
    drw_r_btn = create_semi_circle(
        img_gc,
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
        img_gc,
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
        img_gc,
        x, y, w,
        rotation_deg=0,
        fill="#cccccc"
    )
    x, y = 99, 162
    drw_dd_btn = create_triangle(
        img_gc,
        x, y, w,
        rotation_deg=180,
        fill="#cccccc"
    )
    x, y = 85, 148
    drw_dl_btn = create_triangle(
        img_gc,
        x, y, w,
        rotation_deg=270,
        fill="#cccccc"
    )
    x, y = 113, 148
    drw_dr_btn = create_triangle(
        img_gc,
        x, y, w,
        rotation_deg=90,
        fill="#cccccc"
    )
    
    button_draws.append(drw_start_btn)
    button_draws.append(drw_a_btn)
    button_draws.append(drw_b_btn)
    button_draws.append(drw_x_btn)
    button_draws.append(drw_y_btn)
    button_draws.append(drw_z_btn)
    # note that L and R are excluded from this list because i draw their fill
    # based on how hard they are pressed (analog triggers)
    button_draws.append(drw_du_btn)
    button_draws.append(drw_dd_btn)
    button_draws.append(drw_dl_btn)
    button_draws.append(drw_dr_btn)
    
def create_bean_shape(canvas, cx, cy, cw, ch, steps=10, rotation_deg=0, **kwargs):
    """
    draws a 'bean' shape for X and Y buttons
    taken from https://math.stackexchange.com/a/4642743
    """
    points = []
    for i in range(steps + 1):
        t = 2 * pi * i / steps
        x = 3 + 2 * sin(t) + cos(2 * t)
        y = 4 * cos(t) - sin(2 * t)
        points.append((x, y))

    # Normalize and scale to [0, cw] x [0, ch]
    xs, ys = zip(*points)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    scale_x = cw / (max_x - min_x)
    scale_y = ch / (max_y - min_y)

    # Angle in radians for rotation
    angle_rad = radians(rotation_deg)

    final_points = []
    for x, y in points:
        # Normalize
        nx = (x - min_x) * scale_x - cw / 2
        ny = (y - min_y) * scale_y - ch / 2

        # Rotate
        rx = nx * cos(angle_rad) - ny * sin(angle_rad)
        ry = nx * sin(angle_rad) + ny * cos(angle_rad)

        # Translate to center
        final_points.extend((cx + rx, cy + ry))

    return canvas.create_polygon(final_points, smooth=True, **kwargs)

def create_semi_circle(canvas, cx, cy, cw=100, ch=50, rotation_deg=0,
                       direction="top", steps=10, **kwargs):
    """
    draws a semicircle with rotation controls
    """
    angle_rad = radians(rotation_deg)
    radius_x = cw / 2
    radius_y = ch / 2

    # angle range for top or bottom arc
    if direction == "top":
        angle_start = pi
        angle_end = 0
    else: # bottom
        angle_start = 0
        angle_end = pi

    arc_points = []
    for i in range(steps + 1):
        theta = angle_start + (angle_end - angle_start) * i / steps
        x = radius_x * cos(theta)
        y = radius_y * sin(theta)

        # rotate around (0,0)
        x_rot = x * cos(angle_rad) - y * sin(angle_rad)
        y_rot = x * sin(angle_rad) + y * cos(angle_rad)

        # translate to center
        arc_points.append((cx + x_rot, cy + y_rot))

    # close the semicircle back to center
    arc_points.append((cx, cy))

    return canvas.create_polygon(arc_points, smooth=True, **kwargs)

def create_triangle(canvas, cx, cy, cw=100, rotation_deg=0, **kwargs):
    """
    draws an equilateral triangle centered at (cx, cy) and can be rotated
    """
    height = (sqrt(3) / 2) * cw

    # define points so the centroid is at (0, 0)
    p1 = (0, -height * 2 / 3)  # top
    p2 = (-cw / 2, height / 3) # bottom left
    p3 = (cw / 2, height / 3)  # bottom right

    angle_rad = radians(rotation_deg)

    def rotate_and_translate(x, y):
        # rotate point
        x_rot = x * cos(angle_rad) - y * sin(angle_rad)
        y_rot = x * sin(angle_rad) + y * cos(angle_rad)
        # translate to center
        return (cx + x_rot, cy + y_rot)

    # apply transform
    points = [rotate_and_translate(*p) for p in (p1, p2, p3)]

    return canvas.create_polygon(points, **kwargs)

# timers used for fade effect
button_timers = [0.0] *  10
# list of button draw objects to iterate through when being pressed/fading
button_draws = []

def draw_inputs(frame_index, draw_blank=False):
    # default frame inputs
    frame_inputs = "0:0:0:0:0:0:0:0:0:0:0:0:0:0:128:128:128:128"
    # exit if no DTM loaded
    if not draw_blank:
        if not dtm or len(dtm_inputs) == 0:
            print("no dtm")
            return
        
        # get frame inputs from dtm
        if frame_index <= len(dtm_inputs):
            frame_inputs = dtm_inputs[floor((frame_index - 1) * 4)]
    
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
    img_gc.coords(drw_left_stick, stick_rect)
    
    # position the c stick, same as above
    x, y = (174, 122)
    x += round(10 * (cx - 128) / 128)
    y -= round(10 * (cz - 128) / 128)
    w, h = (x + 52, y + 52)
    stick_rect = (x+14, y+14, w-14, h-14)
    img_gc.coords(drw_c_stick, stick_rect)
    
    # main buttons (Start,      A,          B,          X, Y,               Z        DPAD UDLR)
    btn_colours = ["#b3b3b3", "#00ffff", "#ff0000"] + ["#cccccc"] * 2 + ["#0000c0"] + ["#808080"] * 4
    end_rgb = ["#333333"] * 6 + ["#cccccc"] * 4
    fade_duration = 0.6
    for i, drw_btn in enumerate(button_draws):
        start_rgb = hex_to_rgb(btn_colours[i])
        # if button is just pressed, update timer to now
        if btn[i]: button_timers[i] = time.time()
        # gets duration since last press for fade progress
        dif = time.time() - button_timers[i]
        if dif <= fade_duration:
            eased_t = ease_out_expo(dif / fade_duration) # looks nicer than linear
            # calculates the rgb colour between start and end colour then converts it to hex
            fill = rgb_to_hex(tuple(
                int(start + (end - start) * eased_t)
                for start, end in zip(start_rgb, hex_to_rgb(end_rgb[i]))
            ))
            img_gc.itemconfig(drw_btn, fill=fill) # update colour
    
    # L and R triggers (analog demonstration based on how hard their pressed)
    # the sample video uses a controller without analog triggers so this effect isn't obvious
    start_rgb = hex_to_rgb(btn_colours[0])
    eased_t = 1.0 - ease_out_expo(l / 255) # inverted for fading IN instead of OUT
    # calculates the rgb colour between start and end colour then converts it to hex
    fill = rgb_to_hex(tuple(
        int(start + (end - start) * eased_t)
        for start, end in zip(start_rgb, hex_to_rgb(end_rgb[0]))
    ))
    img_gc.itemconfig(drw_l_btn, fill=fill)
    
    # R trigger
    eased_t = 1.0 - ease_out_expo(r / 255)
    fill = rgb_to_hex(tuple(
        int(start + (end - start) * eased_t)
        for start, end in zip(start_rgb, hex_to_rgb(end_rgb[0]))
    ))
    img_gc.itemconfig(drw_r_btn, fill=fill)

# set custom tkinter appearance and theme
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("themes/lavender.json")

# initialise ctk window title
app = ctk.CTk()
app.title("DTM Visualiser")
# center window on screen
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()
window_width = 1100
window_height = 600
x = (screen_width // 2) - (window_width // 2)
y = (screen_height // 2) - (window_height // 2)
app.geometry(f"{window_width}x{window_height}+{x}+{y}")

# setup a grid layout
app.grid_columnconfigure(0, weight=0) # for the sidebar
app.grid_columnconfigure(1, weight=1) # for canvas which is resizable
app.grid_columnconfigure(2, weight=0) # for gamecube controller, showing inputs
# app.grid_columnconfigure(2, weight=0) # for canvas which is resizable
app.grid_rowconfigure(0, weight=1) # for the top row (sidebar + canvas)
app.grid_rowconfigure(1, weight=0) # for the video player slider
app.grid_rowconfigure(2, weight=0) # for the statusbar

# left-most column
sidebar = ctk.CTkFrame(app)
sidebar.grid(row=0, rowspan=2, column=0, padx=pd, pady=pd, sticky="ns")
sidebar.grid_rowconfigure(0, weight=1)
sidebar.grid_rowconfigure(1, weight=0)

sidebar_upper = ctk.CTkFrame(sidebar, fg_color="transparent")
sidebar_upper.grid(row=0, column=0, padx=0, pady=pd, sticky="nw")


# bottom status bar for loaded labels
statusbar = ctk.CTkFrame(app)
statusbar.grid(row=2, column=0, columnspan=2, padx=pd, pady=pd, sticky="ew")

# canvas for painting the video and elements on top
canvas = VideoPlayer(app)
canvas.grid(row=0, column=1, padx=pd, pady=pd, sticky="nsew")

# gamecube controller for displaying inputs
pil_img = Image.open("images/gc.png")
target_width = 300
aspect_ratio = target_width / pil_img.width

img = ImageTk.PhotoImage(pil_img.resize((target_width, round(pil_img.height * aspect_ratio))))

img_gc = ctk.CTkCanvas(
    app,
    width=img.width(),
    height=img.height(),
    highlightthickness=0,
    bg=app.cget("fg_color")[1]
)
img_gc.grid(row=0, column=2, sticky="nw")
img_gc.create_image(0, 0, anchor="nw", image=img)
init_draws()

# labels
lbl_dtm = ctk.CTkLabel(statusbar, text=get_dtm_text(), font=ctk.CTkFont(size=14))
lbl_dtm.grid(row=0, column=0, sticky="w", padx=pd, pady=0)
lbl_vid = ctk.CTkLabel(statusbar, text=get_vid_text(), font=ctk.CTkFont(size=14))
lbl_vid.grid(row=1, column=0, sticky="w", padx=pd, pady=0)

# buttons
btn_sample = ctk.CTkButton(sidebar_upper, text="Load Sample", command=load_sample, corner_radius=cr)
btn_sample.grid(row=0, column=0, padx=pd, pady=(0, pd))
btn_dtm = ctk.CTkButton(sidebar_upper, text="Load DTM", command=load_dtm, corner_radius=cr)
btn_dtm.grid(row=1, column=0, padx=pd, pady=pd)
btn_video = ctk.CTkButton(sidebar_upper, text="Load Video", command=load_video, corner_radius=cr)
btn_video.grid(row=2, column=0, padx=pd, pady=pd)
btn_unload = ctk.CTkButton(sidebar_upper, text="Unload", command=unload, corner_radius=cr)
btn_unload.grid(row=3, column=0, padx=pd, pady=pd)
# spacer
spacer = ctk.CTkFrame(sidebar_upper, height=20, width=1)
spacer.grid(row=4, column=0, padx=pd, pady=pd)
# preferences
btn_pref = ctk.CTkButton(sidebar_upper, text="Preferences", command=open_pref, corner_radius=cr)
btn_pref.grid(row=5, column=0, padx=pd, pady=pd)
# lower pane
btn_play = ctk.CTkButton(sidebar, text="Play", command=play_video, corner_radius=cr)
btn_play.grid(row=1, column=0, padx=pd, pady=pd)
canvas.play_button = btn_play
canvas.on_frame_update = draw_inputs

# keyboard shortcuts
app.bind("<space>", play_video)
app.bind("<k>", play_video)
app.bind("<Left>", try_seek)
app.bind("<j>", try_seek)
app.bind("<Right>", try_seek)
app.bind("<l>", try_seek)

# playback slider
slider = ctk.CTkSlider(app)

bring_window_to_front() # on macOS if pyobjc is installed
app.mainloop()
