import os
import sqlite3
import json
import uuid
import re
import urllib.request
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify, send_from_directory, render_template, send_file
from werkzeug.utils import secure_filename
from PIL import Image
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 * 1024 # 50GB

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
VIDEOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'videos')
IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
THUMBNAILS_FOLDER = os.path.join(UPLOAD_FOLDER, 'thumbnails')
DB_PATH = os.path.join(BASE_DIR, 'vault.db')

# Seed images folder - images placed here in project are auto-picked up
SEED_IMAGES_FOLDER = os.path.join(BASE_DIR, 'seed_images')

for folder in [VIDEOS_FOLDER, IMAGES_FOLDER, THUMBNAILS_FOLDER, SEED_IMAGES_FOLDER]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_VIDEO = {'mp4', 'webm', 'mov', 'avi', 'mkv', 'ogv'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS links (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            tags TEXT,
            thumbnail TEXT,
            favicon TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            url TEXT,
            filename TEXT,
            embed_code TEXT,
            thumbnail TEXT,
            description TEXT,
            tags TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            tags TEXT,
            source TEXT DEFAULT 'upload',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()

init_db()

def extract_youtube_id(url):
    patterns = [
        r'(?:v=|/v/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def extract_vimeo_id(url):
    m = re.search(r'vimeo\.com/(\d+)', url)
    return m.group(1) if m else None

def fetch_youtube_thumbnail(video_id):
    for quality in ['maxresdefault', 'hqdefault', 'mqdefault']:
        thumb_url = f'https://img.youtube.com/vi/{video_id}/{quality}.jpg'
        try:
            fname = f'yt_{video_id}_{quality}.jpg'
            fpath = os.path.join(THUMBNAILS_FOLDER, fname)
            if not os.path.exists(fpath):
                urllib.request.urlretrieve(thumb_url, fpath)
            return f'/uploads/thumbnails/{fname}'
        except:
            continue
    return None

def fetch_vimeo_thumbnail(video_id):
    try:
        api_url = f'https://vimeo.com/api/v2/video/{video_id}.json'
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())[0]
            thumb_url = data.get('thumbnail_large') or data.get('thumbnail_medium')
            if thumb_url:
                fname = f'vimeo_{video_id}.jpg'
                fpath = os.path.join(THUMBNAILS_FOLDER, fname)
                urllib.request.urlretrieve(thumb_url, fpath)
                return f'/uploads/thumbnails/{fname}'
    except:
        pass
    return None

def fetch_url_favicon(url):
    try:
        parsed = urlparse(url)
        domain = f'{parsed.scheme}://{parsed.netloc}'
        favicon_url = f'https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64'
        fname = f'fav_{parsed.netloc.replace(".", "_")}.png'
        fpath = os.path.join(THUMBNAILS_FOLDER, fname)
        if not os.path.exists(fpath):
            req = urllib.request.Request(favicon_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                with open(fpath, 'wb') as f:
                    f.write(resp.read())
        return f'/uploads/thumbnails/{fname}'
    except:
        return None

def generate_video_thumbnail(filepath, video_id):
    """Try to generate thumbnail from uploaded video using PIL or return None"""
    return None  # ffmpeg not available; frontend handles it

def scan_seed_images():
    """Scan seed_images folder and add any new images to DB"""
    conn = get_db()
    c = conn.cursor()
    existing = {row['filename'] for row in c.execute("SELECT filename FROM images WHERE source='seed'").fetchall()}
    
    image_files = []
    for fname in os.listdir(SEED_IMAGES_FOLDER):
        if allowed_file(fname, ALLOWED_IMAGE):
            image_files.append(fname)
    
    # Sort by numeric name if possible
    def sort_key(f):
        name = os.path.splitext(f)[0]
        try:
            return (0, int(name))
        except:
            return (1, name)
    
    image_files.sort(key=sort_key)
    
    added = 0
    for i, fname in enumerate(image_files):
        if fname not in existing:
            # Copy to images folder
            src = os.path.join(SEED_IMAGES_FOLDER, fname)
            dst = os.path.join(IMAGES_FOLDER, fname)
            if not os.path.exists(dst):
                import shutil
                shutil.copy2(src, dst)
            name = os.path.splitext(fname)[0]
            c.execute(
                "INSERT INTO images (id, title, filename, sort_order, source) VALUES (?, ?, ?, ?, 'seed')",
                (str(uuid.uuid4()), name, fname, i)
            )
            added += 1
    
    conn.commit()
    conn.close()
    return added

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ── LINKS ─────────────────────────────────────────────────────────────────────

@app.route('/api/links', methods=['GET'])
def get_links():
    conn = get_db()
    rows = conn.execute("SELECT * FROM links ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/links', methods=['POST'])
def add_link():
    data = request.json
    lid = str(uuid.uuid4())
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    description = data.get('description', '')
    tags = data.get('tags', '')
    
    if not title or not url:
        return jsonify({'error': 'Title and URL required'}), 400
    
    favicon = fetch_url_favicon(url)
    
    conn = get_db()
    conn.execute(
        "INSERT INTO links (id, title, url, description, tags, favicon) VALUES (?,?,?,?,?,?)",
        (lid, title, url, description, tags, favicon)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM links WHERE id=?", (lid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/links/<lid>', methods=['DELETE'])
def delete_link(lid):
    conn = get_db()
    conn.execute("DELETE FROM links WHERE id=?", (lid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── VIDEOS ────────────────────────────────────────────────────────────────────

@app.route('/api/videos', methods=['GET'])
def get_videos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/videos', methods=['POST'])
def add_video():
    vid = str(uuid.uuid4())
    vtype = request.form.get('type', 'url')  # url | upload | embed
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '')
    tags = request.form.get('tags', '')
    thumbnail = None
    url = None
    filename = None
    embed_code = None

    if not title:
        return jsonify({'error': 'Title required'}), 400

    if vtype == 'url':
        url = request.form.get('url', '').strip()
        if not url:
            return jsonify({'error': 'URL required'}), 400
        yt_id = extract_youtube_id(url)
        vim_id = extract_vimeo_id(url)
        if yt_id:
            thumbnail = fetch_youtube_thumbnail(yt_id)
        elif vim_id:
            thumbnail = fetch_vimeo_thumbnail(vim_id)

    elif vtype == 'upload':
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        f = request.files['file']
        if f and allowed_file(f.filename, ALLOWED_VIDEO):
            filename = f'{vid}_{secure_filename(f.filename)}'
            f.save(os.path.join(VIDEOS_FOLDER, filename))
        else:
            return jsonify({'error': 'Invalid video file'}), 400

    elif vtype == 'embed':
        embed_code = request.form.get('embed_code', '').strip()
        if not embed_code:
            return jsonify({'error': 'Embed code required'}), 400
        # Try to get thumbnail from src in embed
        yt_match = re.search(r'youtube\.com/embed/([A-Za-z0-9_-]{11})', embed_code)
        if yt_match:
            thumbnail = fetch_youtube_thumbnail(yt_match.group(1))

    conn = get_db()
    conn.execute(
        "INSERT INTO videos (id, title, type, url, filename, embed_code, thumbnail, description, tags) VALUES (?,?,?,?,?,?,?,?,?)",
        (vid, title, vtype, url, filename, embed_code, thumbnail, description, tags)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM videos WHERE id=?", (vid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/videos/<vid>', methods=['DELETE'])
def delete_video(vid):
    conn = get_db()
    row = conn.execute("SELECT * FROM videos WHERE id=?", (vid,)).fetchone()
    if row and row['filename']:
        fpath = os.path.join(VIDEOS_FOLDER, row['filename'])
        if os.path.exists(fpath):
            os.remove(fpath)
    conn.execute("DELETE FROM videos WHERE id=?", (vid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── IMAGES ────────────────────────────────────────────────────────────────────

@app.route('/api/images', methods=['GET'])
def get_images():
    scan_seed_images()
    conn = get_db()
    rows = conn.execute("SELECT * FROM images ORDER BY sort_order ASC, title ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/images', methods=['POST'])
def upload_images():
    files = request.files.getlist('files')
    tags = request.form.get('tags', '')
    
    if not files:
        return jsonify({'error': 'No files'}), 400
    
    # Sort files by numeric name
    def sort_key(f):
        name = os.path.splitext(f.filename)[0]
        try:
            return (0, int(name))
        except:
            return (1, name)
    
    files_sorted = sorted(files, key=sort_key)
    
    conn = get_db()
    added = []
    for f in files_sorted:
        if f and allowed_file(f.filename, ALLOWED_IMAGE):
            iid = str(uuid.uuid4())
            original_name = os.path.splitext(f.filename)[0]
            ext = f.filename.rsplit('.', 1)[1].lower()
            stored_name = f'{iid}.{ext}'
            f.save(os.path.join(IMAGES_FOLDER, stored_name))
            
            try:
                sort_num = int(original_name)
            except:
                sort_num = 9999
            
            conn.execute(
                "INSERT INTO images (id, title, filename, sort_order, tags, source) VALUES (?,?,?,?,?,'upload')",
                (iid, original_name, stored_name, sort_num, tags)
            )
            added.append(iid)
    
    conn.commit()
    rows = conn.execute(
        f"SELECT * FROM images WHERE id IN ({','.join('?'*len(added))}) ORDER BY sort_order",
        added
    ).fetchall() if added else []
    conn.close()
    return jsonify([dict(r) for r in rows]), 201

@app.route('/api/images/<iid>', methods=['DELETE'])
def delete_image(iid):
    conn = get_db()
    row = conn.execute("SELECT * FROM images WHERE id=?", (iid,)).fetchone()
    if row:
        fpath = os.path.join(IMAGES_FOLDER, row['filename'])
        if os.path.exists(fpath) and row['source'] != 'seed':
            os.remove(fpath)
        conn.execute("DELETE FROM images WHERE id=?", (iid,))
        conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/images/reorder', methods=['POST'])
def reorder_images():
    order = request.json.get('order', [])  # list of {id, sort_order}
    conn = get_db()
    for item in order:
        conn.execute("UPDATE images SET sort_order=? WHERE id=?", (item['sort_order'], item['id']))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/scan-seed', methods=['POST'])
def trigger_scan():
    added = scan_seed_images()
    return jsonify({'added': added})

@app.route('/api/stats', methods=['GET'])
def stats():
    conn = get_db()
    links = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    images = conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
    conn.close()
    return jsonify({'links': links, 'videos': videos, 'images': images})

if __name__ == '__main__':
    print("🗄️  ResourceVault running at http://localhost:5000")
    print(f"📁 Seed images folder: {SEED_IMAGES_FOLDER}")
    print("   Place numbered images (1.jpg, 2.png…) in seed_images/ and they auto-appear!")
    app.run(debug=True, port=5000)
