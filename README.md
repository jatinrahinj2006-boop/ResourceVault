# 🗄️ ResourceVault

A beautiful, self-hosted resource manager for links, videos, and images — powered by Flask + SQLite.

---

## ✨ Features

- **Links** — Save any URL with auto-fetched favicons, descriptions, and tags
- **Videos** — Add via YouTube/Vimeo URL (auto-fetches thumbnail), upload local files, or paste raw embed code from any platform
- **Images** — Upload a folder of images; they auto-sort by filename number (`1.jpg`, `2.png`…)
- **Seed Images** — Drop images directly into `seed_images/` folder and click "Scan" in the sidebar
- **Search** — Filter across all resources instantly
- **SQLite** — Zero config, single file database (`vault.db`)

---

## 🚀 Quick Start

### 1. Install Python dependencies

```bash
pip install flask pillow requests werkzeug
```

### 2. Run the server

```bash
python app.py
```

### 3. Open in browser

```
http://localhost:5000
```

---

## 📁 Project Structure

```
resourcevault/
├── app.py                  # Flask server
├── vault.db                # SQLite database (auto-created)
├── seed_images/            # ← Drop images here, click "Scan seed_images/" in sidebar
├── uploads/
│   ├── videos/             # Uploaded video files
│   ├── images/             # Uploaded image files
│   └── thumbnails/         # Auto-fetched thumbnails & favicons
└── templates/
    └── index.html          # Full frontend UI
```

---

## 🖼️ Adding Images from the Project Folder (Seed Images)

1. Place your numbered images in the `seed_images/` folder:
   ```
   seed_images/
   ├── 1.jpg
   ├── 2.png
   ├── 3.webp
   └── ...
   ```
2. Click **"⟳ Scan seed_images/"** in the sidebar
3. Images are auto-copied to `uploads/images/` and registered in the DB, sorted by number

> You can also name them with text (e.g. `banner.jpg`) — they'll still be picked up, just sorted alphabetically after numbered ones.

---

## 🎬 Video Types

| Type | How it works |
|------|-------------|
| **URL** | Paste a YouTube or Vimeo link — thumbnail is auto-fetched |
| **Upload** | Upload an MP4/WebM/MOV/AVI/MKV file (up to 500MB) |
| **Embed** | Paste raw `<iframe>` or `<video>` embed code from any platform (Loom, Wistia, Twitch, etc.) |

---

## 🔧 Configuration

Edit the top of `app.py` to change:

```python
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Max upload size (bytes)
```

To change the port:
```python
app.run(debug=True, port=5000)  # Change 5000 to any port
```

---

## 🛠️ Dependencies

- **Flask** — Web framework
- **Pillow** — Image processing
- **Requests** — HTTP for thumbnail fetching
- **Werkzeug** — File upload security (bundled with Flask)
- **SQLite3** — Built into Python, no install needed
