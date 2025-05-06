import cv2
from PIL import Image, ImageTk
from util import log, err, err_popup
import customtkinter as ctk
from customtkinter import filedialog
from tkinter import messagebox
from convert_video import ffmpeg
import sys
import subprocess
from pathlib import Path

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
    if len(filename) == 0:
        log("Unloading DTM file")
        dtm = ""
        lbl_dtm.configure(text=get_dtm_text())
        return
    
    file = Path(filename)
    if not file.exists():
        err_popup(f"DTM file was not found:\n\n{file.absolute()}")
        return
        
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
    
    if not output_fn.exists():
        err_popup(f"Failed to convert DTM file to TXT.\nOutput not found at:\n\n{output_fn}")
        return
    
    dtm = str(file.absolute())
    lbl_dtm.configure(text=get_dtm_text())
    
def set_vid(filename: str, skip_compression: bool = False):
    global vid
    if len(filename) == 0:
        log("Unloading video file")
        vid = ""
        lbl_vid.configure(text=get_vid_text())
        return
    
    file = Path(filename)
    if not file.exists():
        err_popup(f"Video file was not found:\n\n{filename}")
        return
    
    if not skip_compression and messagebox.askyesno(
        "Compress Video",
        "Do you want to compress this video to 480p30 using FFmpeg?\n\n" \
        "NOTE: This requires you to have FFmpeg installed and added to PATH.\n" \
        "Compressed videos are saved in the ./videos/ directory."
    ):
        log("Attempting to compress video...")
        
        # validate videos folder
        videos = basedir / "videos"
        videos.mkdir(exist_ok=True)
        # get pre-determined output file name
        output_fn = basedir / "videos" / f"{file.stem}.mp4"
        # check if compressed file already exists, and if so, asks the user if they want to
        # overwrite it or cancel the operation entirely
        if output_fn.exists():
            if not messagebox.askyesno(
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
            output=str(output_fn.absolute())
        ):
            file = output_fn
    else:
        log("User declined video compression, continuing with existing video")
    
    log(f"Loaded video at: {file.absolute()}")
    vid = str(file.absolute())
    lbl_vid.configure(text=get_vid_text())

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("themes/lavender.json")

app = ctk.CTk()
app.title("DTM Visualiser")
app.geometry("800x600")

# Button callbacks
def load_sample():
    set_dtm("sample/pikmin.dtm")
    set_vid("sample/pikmin.mp4", skip_compression=True)
    
def load_dtm():
    filename = filedialog.askopenfilename(
        filetypes=[(
            "DTM Dolphin Test Movie Files",
            "*.dtm"
        )]
    )
    if filename:
        log(f"Attempting to load DTM at: {filename}")
        set_dtm(filename)
    else:
        log("User cancelled loading DTM")
    
def load_video():
    filename = filedialog.askopenfilename(
        filetypes=[(
            "Video Files",
            "*.mp4;*.avi;*.mov"
        )]
    )
    if filename:
        log(f"Attempting to load video at: {filename}")
        set_vid(filename)
    else:
        log("User cancelled loading video")

def play_video():
    pass
    
def unload(): 
    set_dtm("")
    set_vid("")
    
# left-most column
sidebar = ctk.CTkFrame(app)
sidebar.pack(side="top", anchor="nw", fill="y", padx=pd, pady=pd)

statusbar = ctk.CTkFrame(app)
statusbar.pack(side="bottom", anchor="sw", fill="y", padx=pd, pady=pd)

# labels
lbl_dtm = ctk.CTkLabel(statusbar, text=get_dtm_text(), font=ctk.CTkFont(size=14))
lbl_dtm.grid(row=0, column=0, sticky="w", padx=pd, pady=0)
lbl_vid = ctk.CTkLabel(statusbar, text=get_vid_text(), font=ctk.CTkFont(size=14))
lbl_vid.grid(row=1, column=0, sticky="w", padx=pd, pady=0)

# buttons
btn_sample = ctk.CTkButton(sidebar, text="Load Sample", command=load_sample, corner_radius=cr)
btn_sample.grid(row=2, column=0, padx=pd, pady=pd)
btn_dtm = ctk.CTkButton(sidebar, text="Load DTM", command=load_dtm, corner_radius=cr)
btn_dtm.grid(row=3, column=0, padx=pd, pady=pd)
btn_video = ctk.CTkButton(sidebar, text="Load Video", command=load_video, corner_radius=cr)
btn_video.grid(row=4, column=0, padx=pd, pady=pd)
btn_play = ctk.CTkButton(sidebar, text="Play", command=play_video, corner_radius=cr)
btn_play.grid(row=5, column=0, padx=pd, pady=pd)
btn_unload = ctk.CTkButton(sidebar, text="Unload", command=unload, corner_radius=cr)
btn_unload.grid(row=6, column=0, padx=pd, pady=pd)

app.mainloop()