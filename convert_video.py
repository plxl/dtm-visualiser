import subprocess
import threading
from util import log, err, err_popup

#############
# IMPORTANT #
#############
# This module is used if the user has ffmpeg
# and wants to reduce filesize of the avi

# basic command to convert input to 480p30 with high compression for minimal filesize
command = [
    "ffmpeg",
    "-i", "input.avi",
    "-vf", "scale=-2:480,fps=_FPS_",
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", "25",
    "-c:a", "aac",
    "-b:a", "96k",
    "output.mp4",
    "-y"
]

def read_output(pipe, is_stderr=False):
    try:
        for line in iter(pipe.readline, b''):
            # Decode byte to string and strip newline
            if is_stderr:
                err(line, end='')
            else: print(line, end='')  # Print output in real-time
        pipe.close()
    except ValueError as e:
        exit()

def ffmpeg(input: str, output: str, fps: str) -> bool:
    command[2] = input
    command[-2] = output
    command[4] = command[4].replace("_FPS_", fps)
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Create separate threads for stdout and stderr
        stdout_thread = threading.Thread(target=read_output, args=(proc.stdout,))
        stderr_thread = threading.Thread(target=read_output, args=(proc.stderr,))

        # Start the threads
        stdout_thread.start()
        stderr_thread.start()

        # Wait for the proc to finish
        proc.wait()
        
        # Close the process
        proc.stdout.close()
        proc.stderr.close()
        
        log("Video compression completed")
        return True
    
    except subprocess.CalledProcessError as e:
        err_popup(f"FFmpeg failed with error:\n\n{e.stderr}")
        return False
