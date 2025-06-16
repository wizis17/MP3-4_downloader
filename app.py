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

# Load cookies from JSON file and convert to Netscape format
def load_cookies():
    try:
        # Try to load from file first, then environment variable
        if os.path.exists('cookies.json'):
            with open('cookies.json', 'r') as f:
                cookies_data = json.load(f)
        elif os.environ.get('YOUTUBE_COOKIES_JSON'):
            cookies_data = json.loads(os.environ.get('YOUTUBE_COOKIES_JSON'))
        else:
            print("❌ No cookies.json found. Some videos may not be accessible.")
            return False
        
        # Convert JSON cookies to Netscape format for yt-dlp
        cookies_txt = []
        cookies_txt.append("# Netscape HTTP Cookie File")
        cookies_txt.append("# This is a generated file! Do not edit.")
        cookies_txt.append("")
        
        for cookie in cookies_data:
            # Netscape format: domain, domain_specified, path, secure, expires, name, value
            domain = cookie.get('domain', '.youtube.com')
            if not domain.startswith('.'):
                domain = '.' + domain.lstrip('.')
            
            domain_specified = 'TRUE'
            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            
            # Handle expiration date
            expires = cookie.get('expirationDate')
            if expires is None:
                expires = int(time.time()) + 86400 * 365  # 1 year from now
            else:
                expires = int(float(expires))
            
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            
            # Skip empty cookies
            if not name or not value:
                continue
                
            # Format: domain \t domain_specified \t path \t secure \t expires \t name \t value
            cookie_line = f"{domain}\t{domain_specified}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
            cookies_txt.append(cookie_line)
        
        # Write to cookies.txt file
        with open('cookies.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(cookies_txt))
        
        print(f"✅ Converted {len(cookies_data)} cookies to Netscape format")
        return True
        
    except FileNotFoundError:
        print("❌ cookies.json not found. Some videos may not be accessible.")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in cookies.json: {e}")
        return False
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        return False

# Load cookies on startup
load_cookies()

# Simple in-memory rate limit: {ip: [timestamps]}
rate_limit = {}
MAX_DOWNLOADS_PER_HOUR = 5

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/debug')
def debug():
    json_status = "✅ Found" if os.path.exists('cookies.json') else "❌ Missing"
    txt_status = "✅ Found" if os.path.exists('cookies.txt') else "❌ Missing"
    return f"cookies.json: {json_status}<br>cookies.txt: {txt_status}"

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

    # Enhanced ydl_opts with better bot detection handling
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
        # Add these to help avoid bot detection
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'sleep_interval': 1,
        'max_sleep_interval': 5,
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
        if "sign in to confirm" in error_msg or "bot" in error_msg:
            return "YouTube requires authentication. This video may be restricted or require login.", 400
        elif "private" in error_msg or "unavailable" in error_msg:
            return "Video is private or unavailable. Please check the URL and try again.", 400
        elif "age" in error_msg and "restricted" in error_msg:
            return "Age-restricted video. Cannot download without proper authentication.", 400
        elif "copyright" in error_msg:
            return "Video is copyright protected and cannot be downloaded.", 400
        elif "live" in error_msg:
            return "Live streams cannot be downloaded. Please try after the stream ends.", 400
        else:
            return f"Download failed: Try a different video or check if it's publicly available.", 500
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