from flask import Flask, request, render_template, send_file, abort
from flask_cors import CORS
import yt_dlp
import os
import uuid
import time

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = "download"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Simple in-memory rate limit: {ip: [timestamps]}
rate_limit = {}
MAX_DOWNLOADS_PER_HOUR = 5

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    ip = request.remote_addr
    now = time.time()
    # Clean up old timestamps
    rate_limit.setdefault(ip, [])
    rate_limit[ip] = [t for t in rate_limit[ip] if now - t < 3600]
    if len(rate_limit[ip]) >= MAX_DOWNLOADS_PER_HOUR:
        return "Rate limit exceeded. Try again later.", 429
    rate_limit[ip].append(now)

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
        'cookiefile': 'cookies.txt',  # <-- Add this line
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': audio_quality,
        }] if filetype == 'mp3' else []
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if 'requested_downloads' in info:
            real_path = info['requested_downloads'][0]['filepath']
            ext = real_path.split('.')[-1]
        elif 'filepath' in info:
            real_path = info['filepath']
            ext = real_path.split('.')[-1]
        else:
            ext = 'mp3' if filetype == 'mp3' else info.get('ext', 'mp4')
            real_path = os.path.join(DOWNLOAD_DIR, f"{unique_id}.{ext}") 

    download_name = f"{info.get('title', unique_id)}.{ext}"

    if os.path.exists(real_path):
        return send_file(real_path, as_attachment=True, download_name=download_name)

    return "Failed to download."

if __name__ == '__main__':
    app.run(debug=True, port=5000)