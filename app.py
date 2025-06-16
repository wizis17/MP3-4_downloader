from flask import Flask, request, render_template, send_file, abort
from flask_cors import CORS
import yt_dlp
import os
import uuid
import time
import json

app = Flask(__name__)
CORS(app)

# Add static file handling for production
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_file(f'static/{filename}')

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

    url = request.form.get('url')
    if not url:
        return "URL is required", 400
    
    filetype = request.form.get('filetype', 'mp3')
    quality = request.form.get('quality', 'best')
    audio_quality = request.form.get('audio_quality', '192')
    unique_id = str(uuid.uuid4())
    
    # Set format based on filetype and quality - NO FFmpeg conversion
    if filetype == 'mp3':
        # Download best audio format (m4a/webm) without conversion
        ydl_format = 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best'
        output_path = f"{DOWNLOAD_DIR}/{unique_id}.%(ext)s"
    elif quality == '720':
        ydl_format = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best[height<=720]'
        output_path = f"{DOWNLOAD_DIR}/{unique_id}.%(ext)s"
    elif quality == 'small':
        ydl_format = 'worstvideo+worstaudio/worst'
        output_path = f"{DOWNLOAD_DIR}/{unique_id}.%(ext)s"
    else:  # best
        ydl_format = 'bestvideo+bestaudio/best'
        output_path = f"{DOWNLOAD_DIR}/{unique_id}.%(ext)s"

    # Simple ydl_opts without FFmpeg postprocessors
    ydl_opts = {
        'format': ydl_format,
        'outtmpl': output_path,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'noplaylist': True,
        'ignoreerrors': False,
        'no_warnings': True,
        'extract_flat': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            
            # Check if video is available
            if info.get('availability') and 'private' in info.get('availability', '').lower():
                return "Video is private or unavailable. Please check the URL.", 400
            
            # Now download
            info = ydl.extract_info(url, download=True)
            
            # Find the actual downloaded file
            real_path = None
            ext = None
            
            if 'requested_downloads' in info and info['requested_downloads']:
                real_path = info['requested_downloads'][0]['filepath']
                ext = real_path.split('.')[-1]
            else:
                # Fallback: look for files with our unique_id
                for file in os.listdir(DOWNLOAD_DIR):
                    if file.startswith(unique_id):
                        real_path = os.path.join(DOWNLOAD_DIR, file)
                        ext = file.split('.')[-1]
                        break
            
            if not real_path or not os.path.exists(real_path):
                return "Download completed but file not found. Try a different video.", 500
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "private" in error_msg or "unavailable" in error_msg:
            return "Video is private or unavailable. Please check the URL and try again.", 400
        elif "age" in error_msg and "restricted" in error_msg:
            return "Age-restricted video. Cannot download without proper authentication.", 400
        elif "copyright" in error_msg:
            return "Video is copyright protected and cannot be downloaded.", 400
        elif "live" in error_msg:
            return "Live streams cannot be downloaded. Please try after the stream ends.", 400
        else:
            return f"Download failed: {str(e)}", 500
    except Exception as e:
        return f"Unexpected error: {str(e)}", 500

    # Generate clean filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    download_name = f"{safe_title}.{ext}"

    try:
        return send_file(real_path, as_attachment=True, download_name=download_name)
    except Exception as e:
        return f"Error sending file: {str(e)}", 500
    finally:
        # Clean up downloaded file after sending
        try:
            if real_path and os.path.exists(real_path):
                os.remove(real_path)
        except:
            pass  # Ignore cleanup errors

if __name__ == '__main__':
    print("Starting YouTube Downloader Server...")
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    print(f"🎉 Server starting on port {port}")
    print("Ready to download YouTube videos!")
    app.run(debug=debug_mode, port=port, host='0.0.0.0')