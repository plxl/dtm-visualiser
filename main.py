import cv2
from PIL import Image, ImageTk
from util import log, err, err_popup
import customtkinter as ctk
from customtkinter import filedialog
from tkinter import messagebox, simpledialog
from convert_video import ffmpeg
import sys
import subprocess
from pathlib import Path
from video_player import VideoPlayer

basedir = Path(__file__).resolve().parent
dtm2text = basedir / "dtm2text" / "dtm2text.py"

log(f"Checking for dtm2text at: {dtm2text}")
if not dtm2text.exists():
    err_popup("dtm2text not found. Ensure there is 'dtm2text.py' inside the 'dtm2text' folder.\n\n" \
        "If it's not there, pull the latest version from the repository:\n" \
            "https://github.com/plxl/dtm-visualiser")
    exit()

dtm = ""
vid = ""

corner_radius = cr = 6
padding = pd = 4

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
    
    dtm = str(file.absolute())
    lbl_dtm.configure(text=get_dtm_text())
    
def set_vid(filename: str, skip_compression: bool = False):
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
    
    if not skip_compression:
        # ask if the user wants to compress the video usinf FFmpeg
        result = messagebox.askyesnocancel(
            "Compress Video",
            "Do you want to compress this video to 480p using FFmpeg?\n\n" \
            "NOTE: This requires you to have FFmpeg installed and added to PATH.\n" \
            "Compressed videos are saved in the ./videos/ directory.\n\n" \
            "You will also need to know what framerate your game was running at.\n" \
            "Generally this is 30fps for NTSC and 25fps for PAL."
        )
        if result == True: # pressed Yes
            fps = "a"
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

# set custom tkinter appearance and theme
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("themes/lavender.json")

# initialise ctk window title and size
app = ctk.CTk()
app.title("DTM Visualiser")
app.geometry("800x600")

# button callbacks
def load_sample():
    set_dtm("sample/pikmin.dtm")
    set_vid("sample/pikmin.mp4", skip_compression=True)
    
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
        set_vid(filename)
    
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
    slider.grid_forget()

# setup a grid layout
app.grid_columnconfigure(0, weight=0) # for the sidebar
app.grid_columnconfigure(1, weight=1) # for canvas which is resizable
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
# spacer = ctk.CTkFrame(sidebar_upper, height=20, width=1)
# spacer.grid(row=4, column=0, padx=pd, pady=pd)
btn_play = ctk.CTkButton(sidebar, text="Play", command=play_video, corner_radius=cr)
btn_play.grid(row=1, column=0, padx=pd, pady=pd)
canvas.play_button = btn_play
app.bind("<space>", play_video)
app.bind("<k>", play_video)
app.bind("<Left>", try_seek)
app.bind("<j>", try_seek)
app.bind("<Right>", try_seek)
app.bind("<l>", try_seek)

# playback slider
slider = ctk.CTkSlider(app)

app.mainloop()
