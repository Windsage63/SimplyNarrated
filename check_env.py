import shutil
import os
import subprocess

print(f"ffmpeg path via shutil: {shutil.which('ffmpeg')}")
print(f"ffprobe path via shutil: {shutil.which('ffprobe')}")
print(f"PATH: {os.environ.get('PATH')}")

try:
    res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    print(f"ffmpeg -version output: {res.stdout[:100]}...")
except Exception as e:
    print(f"ffmpeg -version failed: {e}")
