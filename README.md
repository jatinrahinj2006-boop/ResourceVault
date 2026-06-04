# 🗄️ ResourceVault

A beautifully designed, self-hosted, lightweight personal resource manager for archiving links, videos, and images. Powered by a pythonic **Flask** backend and a robust, single-file **SQLite** database.

ResourceVault makes it simple to store, catalog, search, and view your digital assets locally or across a private home network.

---

## ✨ Features

- **🌐 Link Archive**
  - Save links with automated title, tags, and description.
  - Automatically fetches site favicons at high resolution (64px) using Google's Favicon API to use as default card icons.
  - Supports custom thumbnail URL inputs.

- **🎬 Video Gallery**
  - **YouTube & Vimeo Integration:** Paste a video URL, and the server automatically fetches the best quality thumbnail (`maxresdefault`, `hqdefault`, or Vimeo API endpoints).
  - **Local Video Uploads:** Host local files (`.mp4`, `.webm`, `.mov`, `.avi`, `.mkv`, `.ogv`) with support for large files (configured up to 50 GB).
  - **Custom Embeds:** Paste raw `<iframe>` or HTML5 `<video>` codes from Loom, Wistia, Twitch, and more.

- **🖼️ Image Portfolio & Slider**
  - **Batch Upload:** Upload multiple images simultaneously.
  - **Dynamic Reordering:** Rearrange images via drag-and-drop (updates database persistent order sequence).
  - **Seed Directory Scan:** Drop local images directly into the project's `seed_images/` directory and sync them instantly via a one-click scan button.
  - **Smart Numeric Sorting:** Automatically parses and orders numbered filenames (e.g., `1.jpg`, `12.png`, `2.webp`) before sorting alphabetically.

- **🔍 Live Search & Filtering**
  - Real-time client-side search across title descriptions and tags for links, videos, and images.

- **🗃️ Zero Configuration Database**
  - Uses an auto-initializing SQLite database (`vault.db`) requiring no setup or external server dependencies.

---

## 📁 Project Structure

```text
resourcevault/
├── app.py                  # Flask web server & API handlers
├── requirements.txt        # Python dependency manifest
├── vault.db                # SQLite database (auto-created on run)
├── seed_images/            # Directory to drop local images for batch scanning
├── uploads/                # Main assets upload storage directory
│   ├── videos/             # Saved local video files
│   ├── images/             # Saved uploaded & seeded images
│   └── thumbnails/         # Downloaded link/video thumbnails & favicons
└── templates/
    └── index.html          # Dynamic, responsive Tailwind/CSS Frontend UI
```

---

## 🚀 Quick Start

### 1. Prerequisites
Make sure you have **Python 3.8+** installed on your system.

### 2. Install Dependencies
Clone this repository and install the required libraries:
```bash
pip install -r requirements.txt
```

*Or install them manually:*
```bash
pip install flask pillow requests werkzeug gunicorn
```

### 3. Run the Server
Start the Flask application:
```bash
python app.py
```

### 4. Access the Application
Open your browser and navigate to:
```text
http://localhost:5000
```

---

## ⚙️ REST API Reference

ResourceVault communicates via a clean JSON API. You can integrate it with external scripts, browser extensions, or command-line clients.

### 🔗 Links API
* **`GET /api/links`** - Returns list of all saved links (newest first).
* **`POST /api/links`** - Save a new link.
  - **JSON Body:**
    ```json
    {
      "title": "Google",
      "url": "https://google.com",
      "description": "Search Engine",
      "tags": "search,web",
      "thumbnail": "optional_custom_thumbnail_url"
    }
    ```
* **`DELETE /api/links/<lid>`** - Delete link matching `lid`.

### 🎬 Videos API
* **`GET /api/videos`** - Returns list of all videos (newest first).
* **`POST /api/videos`** - Save a new video. Accepts `multipart/form-data`.
  - **Form Fields:**
    - `type`: `url` | `upload` | `embed`
    - `title`: Video Title (Required)
    - `description`: Video description
    - `tags`: Tag strings separated by commas
    - `url`: Video URL (Required if `type` is `url`)
    - `file`: File upload binary (Required if `type` is `upload`)
    - `embed_code`: Raw embed markup (Required if `type` is `embed`)
* **`DELETE /api/videos/<vid>`** - Deletes video matching `vid` (and cleans up local video files if uploaded).

### 🖼️ Images API
* **`GET /api/images`** - Runs seed image check, then returns list of images sorted by sort order.
* **`POST /api/images`** - Upload batch images. Accepts `multipart/form-data`.
  - **Form Fields:**
    - `files`: File array/list of images.
    - `tags`: Tag strings.
* **`POST /api/images/reorder`** - Update layout positions persistently.
  - **JSON Body:**
    ```json
    {
      "order": [
        { "id": "uuid-1", "sort_order": 0 },
        { "id": "uuid-2", "sort_order": 1 }
      ]
    }
    ```
* **`DELETE /api/images/<iid>`** - Deletes image matching `iid` (retains image file if it belongs to the `seed` source).
* **`POST /api/scan-seed`** - Manually trigger a search in `seed_images/` folder for new images.

### 📊 Stats API
* **`GET /api/stats`** - Returns resource count metadata.
  - **JSON Response:**
    ```json
    { "links": 12, "videos": 4, "images": 45 }
    ```

---

## 🗄️ Database Schema

SQLite creates three tables automatically inside `vault.db`:

### `links` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Display title |
| `url` | TEXT | Target link location |
| `description`| TEXT | Description metadata |
| `tags` | TEXT | Comma-delimited tag list |
| `thumbnail`  | TEXT | URL path to thumbnail image |
| `favicon`    | TEXT | URL path to downloaded favicon |
| `created_at` | DATETIME | Automatic timestamp |

### `videos` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Display title |
| `type` | TEXT | Video source: `url`, `upload`, or `embed` |
| `url` | TEXT | External link (YouTube/Vimeo) |
| `filename` | TEXT | Local saved filename under uploads |
| `embed_code` | TEXT | Raw HTML embed string |
| `thumbnail` | TEXT | Thumbnail file path / remote URL |
| `description`| TEXT | Short summary description |
| `tags` | TEXT | Comma-delimited tag list |
| `created_at` | DATETIME | Automatic timestamp |

### `images` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Image title (inferred from filename) |
| `filename` | TEXT | Storage name inside uploads/images |
| `sort_order` | INTEGER | Order priority index (lowest first) |
| `tags` | TEXT | Comma-delimited tag list |
| `source` | TEXT | Source flag: `upload` or `seed` |
| `created_at` | DATETIME | Automatic timestamp |

---

## 🛡️ Production Deployment

For deploying ResourceVault to production or hosting it permanently on a home server (e.g., Raspberry Pi, home lab):

1. **Use a Production WSGI Server:**
   Avoid running `python app.py` (Flask's development server) in production. Instead, run with **Gunicorn**:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
2. **Reverse Proxy (Nginx):**
   Set up Nginx as a reverse proxy to handle SSL termination, request buffering, and serving the `uploads/` static directory directly for optimal performance.
3. **Persist the Database:**
   Ensure `vault.db` and the `uploads/` directories are backed up regularly, as all your media assets and metadata live entirely within these folders.
