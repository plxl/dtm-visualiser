# basic util functions
from datetime import datetime
import tkinter.messagebox as messagebox

def log(message: str, type: str = "LOG"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} [{type}] {message}")
    
def err(message: str):
    log(message, "ERROR")
    
def err_popup(message: str):
    err(message)
    messagebox.showerror("Error", message)