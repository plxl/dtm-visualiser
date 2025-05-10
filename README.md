# DTM Visualiser
Syncs Dolphin frame dump + input recording so you can preview it live

Watch a demonstration video:

https://github.com/user-attachments/assets/40e5229f-4c90-4475-be5d-6a1832c4504b

### Requirements
- Python >= 3.9
- cv2
- PIL
- customtkinter
- FFmpeg (optional, added to PATH)

Install to your virtual environment with:
```
pip install -r requirements.txt
```

### macOS
Tested with Python 3.9.22 on macOS Sequoia 15.4.1. In addition to the aforementioned requirements, you may need to install python-tk if it's not bundled in your Python installation:
```
brew install python-tk
```
