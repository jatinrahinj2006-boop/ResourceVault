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
import requests

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 * 1024 # 50GB

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Persistent storage directory. On platforms with ephemeral filesystems
# (e.g. Render's free tier), set PERSISTENT_DIR to a mounted disk path so
# that vault.db and uploads/ survive restarts.
# Example (Render): add a disk mounted at /data and set PERSISTENT_DIR=/data
PERSISTENT_DIR = os.environ.get('PERSISTENT_DIR', BASE_DIR)
UPLOAD_FOLDER = os.path.join(PERSISTENT_DIR, 'uploads')
VIDEOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'videos')
IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
THUMBNAILS_FOLDER = os.path.join(UPLOAD_FOLDER, 'thumbnails')
DB_PATH = os.path.join(PERSISTENT_DIR, 'vault.db')
PDFS_FOLDER = os.path.join(UPLOAD_FOLDER, 'pdfs')
NOTES_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'notes')

# Seed images folder - images placed here in project are auto-picked up
SEED_IMAGES_FOLDER = os.path.join(PERSISTENT_DIR, 'seed_images')

for folder in [VIDEOS_FOLDER, IMAGES_FOLDER, THUMBNAILS_FOLDER, SEED_IMAGES_FOLDER, PDFS_FOLDER, NOTES_IMAGES_FOLDER]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_VIDEO = {'mp4', 'webm', 'mov', 'avi', 'mkv', 'ogv'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def column_exists(conn, table, column):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r['name'] == column for r in rows)


def ensure_column(conn, table, column_def):
    column_name = column_def.split()[0]
    if not column_exists(conn, table, column_name):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


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
            collection_id TEXT,
            pinned INTEGER DEFAULT 0,
            trashed INTEGER DEFAULT 0,
            deleted_at DATETIME,
            archived INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
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
            collection_id TEXT,
            pinned INTEGER DEFAULT 0,
            trashed INTEGER DEFAULT 0,
            deleted_at DATETIME,
            archived INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            tags TEXT,
            source TEXT DEFAULT 'upload',
            collection_id TEXT,
            chapter_id TEXT,
            pinned INTEGER DEFAULT 0,
            trashed INTEGER DEFAULT 0,
            deleted_at DATETIME,
            archived INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pdfs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            filename TEXT,
            url TEXT,
            description TEXT,
            tags TEXT,
            collection_id TEXT,
            pinned INTEGER DEFAULT 0,
            trashed INTEGER DEFAULT 0,
            deleted_at DATETIME,
            archived INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS collections (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            cover_image TEXT,
            type TEXT NOT NULL,
            pinned INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chapters (
            id TEXT PRIMARY KEY,
            collection_id TEXT NOT NULL,
            title TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS playlists (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            pinned INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS playlist_items (
            id TEXT PRIMARY KEY,
            playlist_id TEXT NOT NULL,
            video_id TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            color TEXT DEFAULT '#7c6af7',
            pinned INTEGER DEFAULT 0,
            trashed INTEGER DEFAULT 0,
            deleted_at DATETIME,
            archived INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            tags TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS custom_sections (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            icon TEXT DEFAULT '📁',
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS custom_items (
            id TEXT PRIMARY KEY,
            section_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            url TEXT,
            filename TEXT,
            type TEXT,
            tags TEXT,
            pinned INTEGER DEFAULT 0,
            trashed INTEGER DEFAULT 0,
            deleted_at DATETIME,
            archived INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS note_images (
            id TEXT PRIMARY KEY,
            note_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    for table, column in [
        ('links', 'collection_id TEXT'),
        ('links', 'pinned INTEGER DEFAULT 0'),
        ('links', 'trashed INTEGER DEFAULT 0'),
        ('links', 'deleted_at DATETIME'),
        ('links', 'archived INTEGER DEFAULT 0'),
        ('links', 'sort_order INTEGER DEFAULT 0'),
        ('videos', 'collection_id TEXT'),
        ('videos', 'pinned INTEGER DEFAULT 0'),
        ('videos', 'trashed INTEGER DEFAULT 0'),
        ('videos', 'deleted_at DATETIME'),
        ('videos', 'archived INTEGER DEFAULT 0'),
        ('videos', 'sort_order INTEGER DEFAULT 0'),
        ('images', 'collection_id TEXT'),
        ('images', 'chapter_id TEXT'),
        ('images', 'pinned INTEGER DEFAULT 0'),
        ('images', 'trashed INTEGER DEFAULT 0'),
        ('images', 'deleted_at DATETIME'),
        ('images', 'archived INTEGER DEFAULT 0'),
        ('pdfs', 'collection_id TEXT'),
        ('pdfs', 'pinned INTEGER DEFAULT 0'),
        ('pdfs', 'trashed INTEGER DEFAULT 0'),
        ('pdfs', 'deleted_at DATETIME'),
        ('pdfs', 'archived INTEGER DEFAULT 0'),
        ('pdfs', 'sort_order INTEGER DEFAULT 0'),
        ('notes', 'pinned INTEGER DEFAULT 0'),
        ('notes', 'trashed INTEGER DEFAULT 0'),
        ('notes', 'deleted_at DATETIME'),
        ('notes', 'archived INTEGER DEFAULT 0'),
        ('notes', 'sort_order INTEGER DEFAULT 0'),
        ('collections', 'pinned INTEGER DEFAULT 0'),
        ('playlists', 'pinned INTEGER DEFAULT 0'),
        ('custom_items', 'pinned INTEGER DEFAULT 0'),
        ('custom_items', 'trashed INTEGER DEFAULT 0'),
        ('custom_items', 'deleted_at DATETIME'),
        ('custom_items', 'archived INTEGER DEFAULT 0'),
        ('custom_items', 'sort_order INTEGER DEFAULT 0')
    ]:
        ensure_column(conn, table, column)

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


def fetch_url_metadata(url):
    """Fetch page title and description from a URL, bypassing regional blocks."""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.72 Mobile Safari/537.36',
    ]
    for ua in user_agents:
        try:
            resp = requests.get(url, headers={
                'User-Agent': ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding
                html = resp.text
                title = None
                desc = None
                m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
                if m:
                    title = m.group(1).strip()
                    title = re.sub(r'\s+', ' ', title)
                m = re.search(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE)
                if not m:
                    m = re.search(r'<meta\s+[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE)
                if m:
                    desc = m.group(1).strip()
                return title or '', desc or ''
        except Exception:
            continue
    return None, None

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

@app.route('/favicon.png')
def favicon_png():
    return send_from_directory(BASE_DIR, 'favicon.png')

@app.route('/logo.png')
def logo_png():
    return send_from_directory(BASE_DIR, 'logo.png')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ── LINKS ─────────────────────────────────────────────────────────────────────

@app.route('/api/links', methods=['GET'])
def get_links():
    conn = get_db()
    rows = conn.execute("SELECT * FROM links WHERE trashed=0 AND archived=0 ORDER BY pinned DESC, sort_order ASC, created_at DESC").fetchall()
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
    thumbnail = data.get('thumbnail', '').strip()
    collection_id = data.get('collection_id') or None
    
    if not title or not url:
        return jsonify({'error': 'Title and URL required'}), 400
    
    conn = get_db()
    existing = conn.execute("SELECT * FROM links WHERE url=?", (url,)).fetchone()
    if existing:
        row = dict(existing)
        conn.close()
        return jsonify({'error': 'duplicate', 'existing': row}), 409
    
    favicon = fetch_url_favicon(url)
    if not thumbnail:
        thumbnail = favicon
    
    conn.execute(
        "INSERT INTO links (id, title, url, description, tags, thumbnail, favicon, collection_id) VALUES (?,?,?,?,?,?,?,?)",
        (lid, title, url, description, tags, thumbnail, favicon, collection_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM links WHERE id=?", (lid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/links/fetch-metadata', methods=['POST'])
def fetch_metadata():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL required'}), 400
    title, description = fetch_url_metadata(url)
    if title is None:
        return jsonify({'error': 'Could not fetch metadata', 'title': '', 'description': ''}), 422
    return jsonify({'title': title, 'description': description})

@app.route('/api/links/<lid>', methods=['DELETE'])
def delete_link(lid):
    conn = get_db()
    conn.execute("UPDATE links SET trashed=1, deleted_at=CURRENT_TIMESTAMP WHERE id=?", (lid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── VIDEOS ────────────────────────────────────────────────────────────────────

@app.route('/api/videos', methods=['GET'])
def get_videos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM videos WHERE trashed=0 AND archived=0 ORDER BY pinned DESC, sort_order ASC, created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/videos', methods=['POST'])
def add_video():
    vid = str(uuid.uuid4())
    vtype = request.form.get('type', 'url')  # url | upload | embed
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '')
    tags = request.form.get('tags', '')
    collection_id = request.form.get('collection_id') or None
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
        conn = get_db()
        existing = conn.execute("SELECT * FROM videos WHERE url=?", (url,)).fetchone()
        if existing:
            row = dict(existing)
            conn.close()
            return jsonify({'error': 'duplicate', 'existing': row}), 409
        yt_id = extract_youtube_id(url)
        vim_id = extract_vimeo_id(url)
        if yt_id:
            thumbnail = fetch_youtube_thumbnail(yt_id)
        elif vim_id:
            thumbnail = fetch_vimeo_thumbnail(vim_id)
        conn.close()

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
        yt_match = re.search(r'youtube\.com/embed/([A-Za-z0-9_-]{11})', embed_code)
        if yt_match:
            thumbnail = fetch_youtube_thumbnail(yt_match.group(1))

    conn = get_db()
    conn.execute(
        "INSERT INTO videos (id, title, type, url, filename, embed_code, thumbnail, description, tags, collection_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (vid, title, vtype, url, filename, embed_code, thumbnail, description, tags, collection_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM videos WHERE id=?", (vid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/videos/<vid>', methods=['DELETE'])
def delete_video(vid):
    conn = get_db()
    conn.execute("UPDATE videos SET trashed=1, deleted_at=CURRENT_TIMESTAMP WHERE id=?", (vid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── IMAGES ────────────────────────────────────────────────────────────────────

@app.route('/api/images', methods=['GET'])
def get_images():
    conn = get_db()
    rows = conn.execute("SELECT * FROM images WHERE trashed=0 AND archived=0 ORDER BY pinned DESC, sort_order ASC, title ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/images', methods=['POST'])
def upload_images():
    files = request.files.getlist('files')
    tags = request.form.get('tags', '')
    collection_id = request.form.get('collection_id') or None
    chapter_id = request.form.get('chapter_id') or None
    
    if not files:
        return jsonify({'error': 'No files'}), 400
    
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
                "INSERT INTO images (id, title, filename, sort_order, tags, source, collection_id, chapter_id) VALUES (?,?,?,?,?,?,?,?)",
                (iid, original_name, stored_name, sort_num, tags, 'upload', collection_id, chapter_id)
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
    conn.execute("UPDATE images SET trashed=1, deleted_at=CURRENT_TIMESTAMP WHERE id=?", (iid,))
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
    links = conn.execute("SELECT COUNT(*) FROM links WHERE trashed=0 AND archived=0").fetchone()[0]
    videos = conn.execute("SELECT COUNT(*) FROM videos WHERE trashed=0 AND archived=0").fetchone()[0]
    images = conn.execute("SELECT COUNT(*) FROM images WHERE trashed=0 AND archived=0").fetchone()[0]
    pdfs = conn.execute("SELECT COUNT(*) FROM pdfs WHERE trashed=0 AND archived=0").fetchone()[0]
    collections = conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
    playlists = conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]
    notes = conn.execute("SELECT COUNT(*) FROM notes WHERE trashed=0 AND archived=0").fetchone()[0]
    custom = conn.execute("SELECT COUNT(*) FROM custom_sections").fetchone()[0]
    conn.close()
    return jsonify({
        'links': links,
        'videos': videos,
        'images': images,
        'pdfs': pdfs,
        'collections': collections,
        'playlists': playlists,
        'notes': notes,
        'custom': custom
    })

# ── PDFS ──────────────────────────────────────────────────────────────────────

@app.route('/api/pdfs', methods=['GET'])
def get_pdfs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM pdfs WHERE trashed=0 AND archived=0 ORDER BY pinned DESC, sort_order ASC, created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/pdfs', methods=['POST'])
def add_pdf():
    pid = str(uuid.uuid4())
    ptype = request.form.get('type', 'upload')  # upload | url
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '')
    tags = request.form.get('tags', '')
    collection_id = request.form.get('collection_id') or None
    filename = None
    url = None

    if not title:
        return jsonify({'error': 'Title required'}), 400

    if ptype == 'url':
        url = request.form.get('url', '').strip()
        if not url:
            return jsonify({'error': 'URL required'}), 400
    elif ptype == 'upload':
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        f = request.files['file']
        if f and f.filename.lower().endswith('.pdf'):
            original_filename = secure_filename(f.filename)
            filename = f'{pid}_{original_filename}'
            conn = get_db()
            existing = conn.execute("SELECT * FROM pdfs WHERE filename LIKE ?", (f'%_{original_filename}',)).fetchone()
            if existing:
                row = dict(existing)
                conn.close()
                return jsonify({'error': 'duplicate', 'existing': row}), 409
            f.save(os.path.join(PDFS_FOLDER, filename))
            conn.close()
        else:
            return jsonify({'error': 'Invalid PDF file'}), 400
    else:
        return jsonify({'error': 'Invalid type'}), 400

    conn = get_db()
    if ptype == 'url':
        existing = conn.execute("SELECT * FROM pdfs WHERE url=? OR filename LIKE ?", (url, f'%_{secure_filename(url)}')).fetchone()
        if existing:
            row = dict(existing)
            conn.close()
            return jsonify({'error': 'duplicate', 'existing': row}), 409

    conn.execute(
        "INSERT INTO pdfs (id, title, type, filename, url, description, tags, collection_id) VALUES (?,?,?,?,?,?,?,?)",
        (pid, title, ptype, filename, url, description, tags, collection_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM pdfs WHERE id=?", (pid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/pdfs/<pid>', methods=['DELETE'])
def delete_pdf(pid):
    conn = get_db()
    conn.execute("UPDATE pdfs SET trashed=1, deleted_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── COLLECTIONS ──────────────────────────────────────────────────────────────

@app.route('/api/collections', methods=['GET'])
def get_collections():
    conn = get_db()
    rows = conn.execute("SELECT * FROM collections ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/collections', methods=['POST'])
def add_collection():
    cid = str(uuid.uuid4())
    data = request.json
    title = data.get('title', '').strip()
    description = data.get('description', '')
    cover_image = data.get('cover_image')
    ctype = data.get('type', 'mixed')
    if not title:
        return jsonify({'error': 'Title required'}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO collections (id, title, description, cover_image, type) VALUES (?,?,?,?,?)",
        (cid, title, description, cover_image, ctype)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM collections WHERE id=?", (cid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/collections/<cid>', methods=['DELETE'])
def delete_collection(cid):
    conn = get_db()
    conn.execute("UPDATE links SET collection_id=NULL WHERE collection_id=?", (cid,))
    conn.execute("UPDATE videos SET collection_id=NULL WHERE collection_id=?", (cid,))
    conn.execute("UPDATE images SET collection_id=NULL WHERE collection_id=?", (cid,))
    conn.execute("UPDATE pdfs SET collection_id=NULL WHERE collection_id=?", (cid,))
    conn.execute("DELETE FROM collections WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/collections/<cid>/items', methods=['POST'])
def assign_collection_item(cid):
    data = request.json
    item_type = data.get('type')
    item_id = data.get('id')
    if item_type not in ('links', 'videos', 'images', 'pdfs'):
        return jsonify({'error': 'Invalid type'}), 400
    conn = get_db()
    conn.execute(f"UPDATE {item_type} SET collection_id=? WHERE id=?", (cid, item_id))
    conn.commit()
    row = conn.execute(f"SELECT * FROM {item_type} WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

# ── CHAPTERS ─────────────────────────────────────────────────────────────────

@app.route('/api/chapters', methods=['GET'])
def get_chapters():
    conn = get_db()
    rows = conn.execute("SELECT * FROM chapters ORDER BY collection_id, sort_order ASC, created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/chapters', methods=['POST'])
def add_chapter():
    cid = str(uuid.uuid4())
    data = request.json
    collection_id = data.get('collection_id')
    title = data.get('title', '').strip()
    sort_order = int(data.get('sort_order') or 0)
    if not collection_id or not title:
        return jsonify({'error': 'Collection and title required'}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO chapters (id, collection_id, title, sort_order) VALUES (?,?,?,?)",
        (cid, collection_id, title, sort_order)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM chapters WHERE id=?", (cid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/chapters/<cid>', methods=['DELETE'])
def delete_chapter(cid):
    conn = get_db()
    conn.execute("UPDATE images SET chapter_id=NULL WHERE chapter_id=?", (cid,))
    conn.execute("DELETE FROM chapters WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── PLAYLISTS ───────────────────────────────────────────────────────────────

@app.route('/api/playlists', methods=['GET'])
def get_playlists():
    conn = get_db()
    rows = conn.execute(
        "SELECT p.*, COALESCE(COUNT(pi.id), 0) AS item_count"
        " FROM playlists p"
        " LEFT JOIN playlist_items pi ON pi.playlist_id = p.id"
        " GROUP BY p.id"
        " ORDER BY p.created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/playlists', methods=['POST'])
def add_playlist():
    pid = str(uuid.uuid4())
    data = request.json
    title = data.get('title', '').strip()
    description = data.get('description', '')
    if not title:
        return jsonify({'error': 'Title required'}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO playlists (id, title, description) VALUES (?,?,?)",
        (pid, title, description)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM playlists WHERE id=?", (pid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/playlists/<pid>', methods=['DELETE'])
def delete_playlist(pid):
    conn = get_db()
    conn.execute("DELETE FROM playlist_items WHERE playlist_id=?", (pid,))
    conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/playlists/<pid>/items', methods=['POST'])
def add_playlist_item(pid):
    data = request.json
    video_id = data.get('video_id')
    if not video_id:
        return jsonify({'error': 'Video required'}), 400
    conn = get_db()
    max_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM playlist_items WHERE playlist_id=?", (pid,)).fetchone()[0]
    item_uuid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO playlist_items (id, playlist_id, video_id, sort_order) VALUES (?,?,?,?)",
        (item_uuid, pid, video_id, max_order + 1)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM playlist_items WHERE id=?", (item_uuid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/playlists/<pid>/items', methods=['DELETE'])
def delete_playlist_item(pid):
    data = request.json
    item_id = data.get('id')
    if not item_id:
        return jsonify({'error': 'Item id required'}), 400
    conn = get_db()
    conn.execute("DELETE FROM playlist_items WHERE id=? AND playlist_id=?", (item_id, pid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/playlists/<pid>/items', methods=['GET'])
def get_playlist_items(pid):
    conn = get_db()
    rows = conn.execute("SELECT * FROM playlist_items WHERE playlist_id=? ORDER BY sort_order ASC", (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ── NOTES ────────────────────────────────────────────────────────────────────

@app.route('/api/notes', methods=['GET'])
def get_notes():
    conn = get_db()
    rows = conn.execute("""
        SELECT n.*, COALESCE((SELECT COUNT(*) FROM note_images WHERE note_id = n.id), 0) as image_count
        FROM notes n
        WHERE trashed=0 AND archived=0
        ORDER BY pinned DESC, sort_order ASC, created_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/notes', methods=['POST'])
def add_note():
    nid = str(uuid.uuid4())
    data = request.json
    title = data.get('title', '').strip()
    content = data.get('content', '')
    color = data.get('color', '#7c6af7')
    tags = data.get('tags', '')
    if not title:
        return jsonify({'error': 'Title required'}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO notes (id, title, content, color, tags) VALUES (?,?,?,?,?)",
        (nid, title, content, color, tags)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM notes WHERE id=?", (nid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/notes/<nid>', methods=['PATCH'])
def patch_note(nid):
    data = request.json
    fields = []
    params = []
    for key in ('title', 'content', 'color', 'tags', 'pinned'):
        if key in data:
            fields.append(f"{key}=?")
            params.append(data[key])
    if not fields:
        return jsonify({'error': 'No fields to update'}), 400
    params.append(nid)
    conn = get_db()
    conn.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    row = conn.execute("SELECT * FROM notes WHERE id=?", (nid,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/notes/<nid>', methods=['DELETE'])
def delete_note(nid):
    conn = get_db()
    # Delete associated note images from disk
    image_rows = conn.execute("SELECT filename FROM note_images WHERE note_id=?", (nid,)).fetchall()
    for row in image_rows:
        path = os.path.join(NOTES_IMAGES_FOLDER, row['filename'])
        if os.path.exists(path):
            os.remove(path)
    # Delete note images from database
    conn.execute("DELETE FROM note_images WHERE note_id=?", (nid,))
    # Soft delete note
    conn.execute("UPDATE notes SET trashed=1, deleted_at=CURRENT_TIMESTAMP WHERE id=?", (nid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── NOTE IMAGES ──────────────────────────────────────────────────────────────

@app.route('/api/notes/<nid>/images', methods=['GET'])
def get_note_images(nid):
    conn = get_db()
    rows = conn.execute("SELECT * FROM note_images WHERE note_id=? ORDER BY sort_order ASC", (nid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/notes/<nid>/images', methods=['POST'])
def upload_note_images(nid):
    files = request.files.getlist('files')
    
    if not files:
        return jsonify({'error': 'No files'}), 400
    
    conn = get_db()
    max_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM note_images WHERE note_id=?", (nid,)).fetchone()[0]
    
    added = []
    for f in files:
        if f and allowed_file(f.filename, ALLOWED_IMAGE):
            img_id = str(uuid.uuid4())
            ext = f.filename.rsplit('.', 1)[1].lower()
            filename = f'{img_id}.{ext}'
            f.save(os.path.join(NOTES_IMAGES_FOLDER, filename))
            
            conn.execute(
                "INSERT INTO note_images (id, note_id, filename, sort_order) VALUES (?,?,?,?)",
                (img_id, nid, filename, max_order + 1)
            )
            added.append(img_id)
            max_order += 1
    
    conn.commit()
    rows = conn.execute(
        f"SELECT * FROM note_images WHERE id IN ({','.join('?'*len(added))}) ORDER BY sort_order",
        added
    ).fetchall() if added else []
    conn.close()
    return jsonify([dict(r) for r in rows]), 201

@app.route('/api/notes/<nid>/images/<img_id>', methods=['DELETE'])
def delete_note_image(nid, img_id):
    conn = get_db()
    row = conn.execute("SELECT filename FROM note_images WHERE id=? AND note_id=?", (img_id, nid)).fetchone()
    if row:
        path = os.path.join(NOTES_IMAGES_FOLDER, row['filename'])
        if os.path.exists(path):
            os.remove(path)
    conn.execute("DELETE FROM note_images WHERE id=? AND note_id=?", (img_id, nid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/notes/<nid>/images/reorder', methods=['POST'])
def reorder_note_images(nid):
    order = request.json.get('order', [])  # list of {id, sort_order}
    conn = get_db()
    for item in order:
        conn.execute("UPDATE note_images SET sort_order=? WHERE id=? AND note_id=?", (item['sort_order'], item['id'], nid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── TRASH / ARCHIVE / STORAGE ─────────────────────────────────────────────────

@app.route('/api/trash', methods=['GET'])
def get_trash():
    conn = get_db()
    results = []
    for item_type in ['links', 'videos', 'images', 'pdfs', 'notes', 'custom_items']:
        rows = conn.execute(f"SELECT * FROM {item_type} WHERE trashed=1 ORDER BY deleted_at DESC").fetchall()
        for row in rows:
            item = dict(row)
            item['type'] = item_type
            results.append(item)
    conn.close()
    return jsonify(results)

@app.route('/api/archive', methods=['GET'])
def get_archive():
    conn = get_db()
    results = []
    for item_type in ['links', 'videos', 'images', 'pdfs', 'notes', 'custom_items']:
        rows = conn.execute(f"SELECT * FROM {item_type} WHERE archived=1 AND trashed=0 ORDER BY created_at DESC").fetchall()
        for row in rows:
            item = dict(row)
            item['type'] = item_type
            results.append(item)
    conn.close()
    return jsonify(results)

@app.route('/api/<item_type>/<item_id>/restore', methods=['PATCH'])
def restore_item(item_type, item_id):
    table_map = {
        'links': 'links',
        'videos': 'videos',
        'images': 'images',
        'pdfs': 'pdfs',
        'notes': 'notes',
        'custom_items': 'custom_items'
    }
    table = table_map.get(item_type)
    if not table:
        return jsonify({'error': 'Invalid item type'}), 400
    conn = get_db()
    conn.execute(f"UPDATE {table} SET trashed=0, deleted_at=NULL WHERE id=?", (item_id,))
    conn.commit()
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/<item_type>/<item_id>/archive', methods=['PATCH'])
def toggle_archive(item_type, item_id):
    table_map = {
        'links': 'links',
        'videos': 'videos',
        'images': 'images',
        'pdfs': 'pdfs',
        'notes': 'notes',
        'custom_items': 'custom_items'
    }
    table = table_map.get(item_type)
    if not table:
        return jsonify({'error': 'Invalid item type'}), 400
    conn = get_db()
    row = conn.execute(f"SELECT archived FROM {table} WHERE id=?", (item_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    new_val = 0 if row['archived'] else 1
    conn.execute(f"UPDATE {table} SET archived=? WHERE id=?", (new_val, item_id))
    conn.commit()
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/<item_type>/<item_id>/permanent', methods=['DELETE'])
def delete_permanent(item_type, item_id):
    table_map = {
        'links': 'links',
        'videos': 'videos',
        'images': 'images',
        'pdfs': 'pdfs',
        'notes': 'notes',
        'custom_items': 'custom_items'
    }
    table = table_map.get(item_type)
    if not table:
        return jsonify({'error': 'Invalid item type'}), 400
    conn = get_db()
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
    if row:
        if table == 'videos' and row['filename']:
            path = os.path.join(VIDEOS_FOLDER, row['filename'])
            if os.path.exists(path):
                os.remove(path)
        elif table == 'images' and row['filename'] and row.get('source') != 'seed':
            path = os.path.join(IMAGES_FOLDER, row['filename'])
            if os.path.exists(path):
                os.remove(path)
        elif table == 'pdfs' and row['type'] == 'upload' and row['filename']:
            path = os.path.join(PDFS_FOLDER, row['filename'])
            if os.path.exists(path):
                os.remove(path)
    conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/trash/empty', methods=['DELETE'])
def empty_trash():
    conn = get_db()
    for table in ['links', 'videos', 'images', 'pdfs', 'notes', 'custom_items']:
        if table == 'videos':
            rows = conn.execute("SELECT * FROM videos WHERE trashed=1").fetchall()
            for row in rows:
                if row['filename']:
                    path = os.path.join(VIDEOS_FOLDER, row['filename'])
                    if os.path.exists(path):
                        os.remove(path)
        elif table == 'images':
            rows = conn.execute("SELECT * FROM images WHERE trashed=1").fetchall()
            for row in rows:
                if row['filename'] and row['source'] != 'seed':
                    path = os.path.join(IMAGES_FOLDER, row['filename'])
                    if os.path.exists(path):
                        os.remove(path)
        elif table == 'pdfs':
            rows = conn.execute("SELECT * FROM pdfs WHERE trashed=1").fetchall()
            for row in rows:
                if row['type'] == 'upload' and row['filename']:
                    path = os.path.join(PDFS_FOLDER, row['filename'])
                    if os.path.exists(path):
                        os.remove(path)
        conn.execute(f"DELETE FROM {table} WHERE trashed=1")
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/<item_type>/reorder', methods=['POST'])
def reorder_items(item_type):
    payload = request.get_json(force=True)
    order = payload.get('order') if isinstance(payload, dict) else None
    if not isinstance(order, list):
        return jsonify({'error': 'Order array required'}), 400
    table_map = {
        'links': 'links',
        'videos': 'videos',
        'pdfs': 'pdfs',
        'notes': 'notes',
        'custom_items': 'custom_items'
    }
    table = table_map.get(item_type)
    if not table:
        return jsonify({'error': 'Invalid item type'}), 400
    conn = get_db()
    for idx, item_id in enumerate(order):
        conn.execute(f"UPDATE {table} SET sort_order=? WHERE id=?", (idx + 1, item_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/storage', methods=['GET'])
def get_storage():
    def folder_info(folder):
        if not os.path.exists(folder):
            return {'count': 0, 'size': 0}
        count = 0
        size = 0
        for root, _, files in os.walk(folder):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp):
                    count += 1
                    size += os.path.getsize(fp)
        return {'count': count, 'size': size}
    data = {
        'uploads': folder_info(UPLOAD_FOLDER),
        'images': folder_info(IMAGES_FOLDER),
        'videos': folder_info(VIDEOS_FOLDER),
        'pdfs': folder_info(PDFS_FOLDER),
        'thumbnails': folder_info(THUMBNAILS_FOLDER)
    }
    return jsonify(data)

@app.route('/api/storage/thumbnails', methods=['DELETE'])
def clear_thumbnails():
    deleted = 0
    if os.path.exists(THUMBNAILS_FOLDER):
        for fname in os.listdir(THUMBNAILS_FOLDER):
            path = os.path.join(THUMBNAILS_FOLDER, fname)
            if os.path.isfile(path):
                os.remove(path)
                deleted += 1
    return jsonify({'deleted': deleted})

# ── CUSTOM SECTIONS ─────────────────────────────────────────────────────────

@app.route('/api/custom-sections', methods=['GET'])
def get_custom_sections():
    conn = get_db()
    rows = conn.execute("SELECT * FROM custom_sections ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/custom-sections', methods=['POST'])
def add_custom_section():
    payload = request.get_json(force=True)
    title = payload.get('title')
    icon = payload.get('icon', '📁')
    description = payload.get('description', '')
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    conn = get_db()
    section_id = str(uuid.uuid4())
    conn.execute("INSERT INTO custom_sections (id, title, icon, description) VALUES (?, ?, ?, ?)",
                 (section_id, title, icon, description))
    conn.commit()
    row = conn.execute("SELECT * FROM custom_sections WHERE id=?", (section_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/custom-sections/<sid>', methods=['DELETE'])
def delete_custom_section(sid):
    conn = get_db()
    conn.execute("DELETE FROM custom_items WHERE section_id=?", (sid,))
    conn.execute("DELETE FROM custom_sections WHERE id=?", (sid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/custom-items', methods=['GET'])
def get_custom_items():
    section_id = request.args.get('section_id')
    conn = get_db()
    if section_id:
        rows = conn.execute("SELECT * FROM custom_items WHERE section_id=? AND trashed=0 AND archived=0 ORDER BY pinned DESC, sort_order ASC, created_at DESC", (section_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM custom_items WHERE trashed=0 AND archived=0 ORDER BY pinned DESC, sort_order ASC, created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/custom-items', methods=['POST'])
def add_custom_item():
    payload = request.get_json(force=True)
    section_id = payload.get('section_id')
    title = payload.get('title')
    if not section_id or not title:
        return jsonify({'error': 'Section and title are required'}), 400
    conn = get_db()
    item_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO custom_items (id, section_id, title, content, url, filename, type, tags, pinned, trashed, archived, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)",
        (item_id, section_id, title, payload.get('content', ''), payload.get('url', ''), payload.get('filename', ''), payload.get('type', 'note'), payload.get('tags', ''))
    )
    conn.commit()
    row = conn.execute("SELECT * FROM custom_items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/custom-items/<cid>', methods=['PATCH'])
def update_custom_item(cid):
    payload = request.get_json(force=True)
    updates = []
    values = []
    for key in ['title', 'content', 'url', 'filename', 'type', 'tags', 'pinned', 'trashed', 'archived', 'sort_order']:
        if key in payload:
            updates.append(f"{key}=?")
            values.append(payload[key])
    if not updates:
        return jsonify({'error': 'No updates provided'}), 400
    values.append(cid)
    conn = get_db()
    conn.execute(f"UPDATE custom_items SET {', '.join(updates)} WHERE id=?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM custom_items WHERE id=?", (cid,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/custom-items/<cid>', methods=['DELETE'])
def delete_custom_item(cid):
    conn = get_db()
    conn.execute("UPDATE custom_items SET trashed=1, deleted_at=CURRENT_TIMESTAMP WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── EXPORT / IMPORT ──────────────────────────────────────────────────────────

@app.route('/api/export', methods=['GET'])
def export_all():
    conn = get_db()
    data = {}
    for table in ['links', 'videos', 'images', 'pdfs', 'collections', 'chapters', 'playlists', 'playlist_items', 'notes', 'custom_sections', 'custom_items']:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        data[table] = [dict(r) for r in rows]
    conn.close()
    return jsonify(data)

@app.route('/api/import', methods=['POST'])
def import_all():
    payload = request.get_json(force=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'Invalid import payload'}), 400
    conn = get_db()
    for table, rows in payload.items():
        if table not in ['links', 'videos', 'images', 'pdfs', 'collections', 'chapters', 'playlists', 'playlist_items', 'notes', 'custom_sections', 'custom_items']:
            continue
        if not isinstance(rows, list):
            continue
        if not rows:
            continue
        cols = list(rows[0].keys())
        placeholders = ','.join(['?'] * len(cols))
        sql = f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        for row in rows:
            conn.execute(sql, [row.get(c) for c in cols])
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── PIN / FAVORITE ──────────────────────────────────────────────────────────

@app.route('/api/<item_type>/<item_id>/pin', methods=['PATCH'])
def toggle_pin(item_type, item_id):
    table_map = {
        'links': 'links',
        'videos': 'videos',
        'images': 'images',
        'pdfs': 'pdfs',
        'notes': 'notes',
        'collections': 'collections',
        'playlists': 'playlists'
    }
    table = table_map.get(item_type)
    if not table:
        return jsonify({'error': 'Invalid item type'}), 400
    conn = get_db()
    row = conn.execute(f"SELECT pinned FROM {table} WHERE id=?", (item_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    new_val = 0 if row['pinned'] else 1
    conn.execute(f"UPDATE {table} SET pinned=? WHERE id=?", (new_val, item_id))
    conn.commit()
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

if __name__ == '__main__':
    print("🗄️  ResourceVault running at http://localhost:5000")
    print(f"📁 Seed images folder: {SEED_IMAGES_FOLDER}")
    print("   Place numbered images (1.jpg, 2.png…) in seed_images/ and they auto-appear!")
    app.run(debug=True, port=5000)
