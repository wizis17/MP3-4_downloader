from flask import Flask, request, render_template, send_file
import yt_dlp
import os
import uuid
import sys

# Add your project directory to the sys.path
project_home = '/home/Theng/mp3_download'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Activate your virtualenv
activate_this = '/home/Theng/mp3_download/venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

from app import app as application

app = Flask(__name__)
DOWNLOAD_DIR = "download"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    filetype = request.form['filetype']
    quality = request.form.get('quality', 'best')
    audio_quality = request.form.get('audio_quality', '192')
    unique_id = str(uuid.uuid4())
    output_path = f"{DOWNLOAD_DIR}/{unique_id}.%(ext)s"

    if filetype == 'mp3':
        ydl_format = 'bestaudio/best'
    elif quality == '720':
        ydl_format = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best[height<=720]'
    elif quality == 'small':
        ydl_format = 'worstvideo+worstaudio/worst'
    else:  # best
        ydl_format = 'bestvideo+bestaudio/best'

    ydl_opts = {
        'format': ydl_format,
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': audio_quality,
        }] if filetype == 'mp3' else []
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Get the actual output filename from yt_dlp
        if 'requested_downloads' in info:
            real_path = info['requested_downloads'][0]['filepath']
        elif 'filepath' in info:
            real_path = info['filepath']
        else:
            ext = 'mp3' if filetype == 'mp3' else info.get('ext', 'mp4')
            real_path = os.path.join(DOWNLOAD_DIR, f"{unique_id}.{ext}")

    # Use the video title for the download name
    download_name = f"{info['title']}.{ext}"

    if os.path.exists(real_path):
        return send_file(real_path, as_attachment=True, download_name=download_name)

    return "Failed to download."

if __name__ == '__main__':
    app.run(debug=True)
