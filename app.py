from flask import Flask, request, render_template, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid

app = Flask(__name__)
CORS(app)  # Or: CORS(app, origins=["https://your-firebase-project.web.app"])

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
            ext = real_path.split('.')[-1]
        elif 'filepath' in info:
            real_path = info['filepath']
            ext = real_path.split('.')[-1]
        else:
            ext = 'mp3' if filetype == 'mp3' else info.get('ext', 'mp4')
            real_path = os.path.join(DOWNLOAD_DIR, f"{unique_id}.{ext}")

    # Use the video title for the download name
    download_name = f"{info.get('title', unique_id)}.{ext}"

    if os.path.exists(real_path):
        return send_file(real_path, as_attachment=True, download_name=download_name)

    return "Failed to download."

if __name__ == '__main__':
    app.run(debug=True)