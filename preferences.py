import customtkinter as ctk
from pathlib import Path
import json
from util import err_popup

# option class makes it easy to handle defaults and known options when parsing settings file
class Option():
    def __init__(self, default, options: list):
        self.default = default
        self.options = options
        self.value = default

# make preferences class for handling all settings from loading, defaults, settng, etc.
class Preferences():
    def __init__(self):
        self.options: dict[str, Option] = dict()
        # initialise settings options here
        self.add_option("compress_video", "Ask", ["Ask", "Always", "Never"])
        self.add_option("compress_video_fps", "25", [])
        # load from file if it exists, and save it if it doesn't
        self.load_settings()
        self.save_settings()
        
    def add_option(self, option: str, default, options: list):
        self.options[option] = Option(default, options)

    def load_settings(self):
        # carefully parse the settings.json file so only valid settings and valid options are read
        settings = Path("settings.json")
        if settings.exists() and settings.is_file():
            loaded = json.loads(settings.read_text())
            for option in self.options.keys():
                if option in loaded.keys() and (
                    len(self.options[option].options) == 0 or \
                    loaded[option] in self.options[option].options
                ):
                    self.options[option].value = loaded[option]
    
    def restore_defaults(self, save_after = True):
        for option in self.options.keys():
            self.options[option].value = self.options[option].default
        if save_after: self.save_settings()
                    
    def save_settings(self):
        settings = Path("settings.json")
        if settings.exists() and not settings.is_file():
            err_popup("Unable to create settings file, please remove or rename the folder at:\n\n" +
                      settings.resolve())
            return
        
        out = {}
        for option in self.options.keys():
            out[option] = self.options[option].value
        # create settings.json if it doesnt exist and write our object as a json
        settings.touch(exist_ok=True)
        settings.write_text(json.dumps(out, indent=4))

class PreferencesWindow(ctk.CTkToplevel):
    def __init__(self, master, preferences: Preferences):
        super().__init__(master)
        self.settings = preferences
        
        self.title("Preferences")
        self.geometry("200x220")
        self.resizable(False, False)

        self.transient(master)
        self.grab_set()
        self._center_window(master)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)
        
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, padx=4, pady=4, sticky="nesw")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_columnconfigure(0, weight=1)
        
        frame_upper = ctk.CTkFrame(frame, fg_color="transparent")
        frame_upper.grid(row=0, column=0, padx=0, pady=4, sticky="nesw")
        frame_upper.grid_columnconfigure(0, weight=1)
        
        lbl_compress_video = ctk.CTkLabel(frame_upper, text="FFmpeg Video Compression", font=ctk.CTkFont(size=14))
        lbl_compress_video.grid(row=0, column=0, sticky="nw", padx=4, pady=0)
        self.cmb_compress_video = ctk.CTkComboBox(frame_upper, command=self.cmb_compress_video_select, values=[
            "Ask",
            "Always",
            "Never"
        ])
        self.cmb_compress_video.grid(row=1, column=0, padx=4, pady=(0, 4), sticky="nw")
        self.cmb_compress_video.bind("<Key>", lambda e: "break") # stops typing in the cmb text field
        self.cmb_compress_video.set(self.settings.options["compress_video"].value)
        
        self.lbl_video_fps = ctk.CTkLabel(frame_upper, text="FPS", font=ctk.CTkFont(size=14))
        self.video_fps = ctk.StringVar()
        self.video_fps.set(self.settings.options["compress_video_fps"].value)
        vcmd = (self.register(self.valid_number), "%P")
        self.num_video_fps = ctk.CTkEntry(
            frame_upper,
            textvariable=self.video_fps,
            validate="key",
            validatecommand=vcmd
        )
        self.update_video_fps_visibility()

        restore_btn = ctk.CTkButton(frame, text="Restore Defaults", command=self.restore_defaults)
        restore_btn.grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        
        close_btn = ctk.CTkButton(self, text="OK", width=60, command=self.close)
        close_btn.grid(row=1, column=0, padx=4, pady=4, sticky="se")
        
    def restore_defaults(self):
        self.settings.restore_defaults()
        self.cmb_compress_video.set(self.settings.options["compress_video"].value)
        self.update_video_fps_visibility()
    
    def cmb_compress_video_select(self, value):
        self.settings.options["compress_video"].value = value
        self.settings.save_settings()
        self.update_video_fps_visibility()
    
    def update_video_fps_visibility(self):
        value = self.settings.options["compress_video"].value
        # if the user wants to auto compress always, we need a default framerate
        # the user should set this to 25 if they use PAL games, 30 for NTSC
        if value == "Always":
            self.lbl_video_fps.grid(row=3, column=0, sticky="nw", padx=4, pady=(4, 0))
            self.num_video_fps.grid(row=4, column=0, sticky="nw", padx=4, pady=(0, 4))
        else:
            self.lbl_video_fps.grid_forget()
            self.num_video_fps.grid_forget()
        
    def valid_number(self, new_value):
        return new_value.isdigit() or new_value == ""

    def _center_window(self, parent):
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        x = parent_x + (parent_width // 2) - (window_width // 2)
        y = parent_y + (parent_height // 2) - (window_height // 2)
        self.geometry(f"+{x}+{y}")

    def close(self):
        self.grab_release()
        self.destroy()
