# basic util functions
from datetime import datetime
import tkinter.messagebox as messagebox
import platform

def log(message: str, type: str = "LOG"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} [{type}] {message}")
    
def err(message: str):
    log(message, "ERROR")
    
def err_popup(message: str):
    err(message)
    messagebox.showerror("Error", message)

def ease_out_expo(t):
    return 1 - pow(2, -10 * t) if t < 1 else 1

def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def bring_window_to_front():
    if platform.system() == "Darwin":
        try:
            from AppKit import NSApplication, NSApp
            NSApplication.sharedApplication()
            NSApp.activateIgnoringOtherApps_(True)

        except Exception as e:
            err(f"[macOS] Failed to bring window to front. " \
                "This can optionally be fixed by running:\n    pip install pyobjc\n")
