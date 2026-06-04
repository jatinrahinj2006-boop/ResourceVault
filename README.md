# 🗄️ ResourceVault

A beautifully designed, self-hosted, lightweight personal resource manager for archiving links, videos, and images. Powered by a pythonic **Flask** backend and a robust, single-file **SQLite** database.

ResourceVault makes it simple to store, catalog, search, and view your digital assets locally or across a private home network.

---

## ✨ Features

- **🌐 Link Archive**
  - Save links with optional title, description, tags, and custom thumbnail URL.
  - Automatically fetches site favicons for richer cards.
  - Add links to collections for better organization.
  - Copy, open, pin, archive, trash, and restore link resources.

- **🎬 Video Gallery**
  - Add videos via URL, upload local files, or paste embed code.
  - Supports YouTube, Vimeo, direct video URLs, and raw embed markup.
  - Build playlists and queue videos for playback.
  - Pin, archive, trash, and manage videos from the workspace.

- **🖼️ Image Portfolio**
  - Upload multiple images at once with tags and collection support.
  - Scan the `seed_images/` folder to import local images instantly.
  - Assign chapters and persist image order for galleries.
  - Gallery view adapts to desktop and mobile layouts.

- **📄 PDF Library**
  - Store both PDF uploads and external PDF URLs.
  - Add descriptions, tags, and collection associations.
  - Open, copy, pin, archive, and delete PDFs from the workspace.

- **📁 Collections**
  - Create collections to group links, videos, images, and PDFs.
  - Each collection can have a custom cover image and description.
  - View item counts and open collections to see grouped content.

- **🎧 Playlists**
  - Create playlists and add videos directly from video cards.
  - Open playlists to play a queued video list.
  - Manage playlists with pin, open, and delete actions.

- **🗒️ Notes**
  - Capture notes with titles, colors, and tags.
  - Pin important notes and archive or trash old ones.
  - Notes display as cards in a dedicated workspace section.

- **🗃️ Workspace Controls**
  - Archive items to keep them safe and out of the main workspace.
  - Trash items for restoration or permanent deletion.
  - Custom sections allow flexible workspace grouping of items.
  - Bulk selection mode supports multi-item actions.

- **🔍 Smart Search & Filters**
  - Search across titles, descriptions, tags, and metadata.
  - Toggle pinned items to surface favorites.
  - Live filtering updates results instantly.

- **📱 Mobile-first UI**
  - Sidebar hides on mobile; bottom nav provides quick access.
  - Floating action button (FAB) adds new resources on small screens.
  - Pull-to-refresh refreshes the current section.
  - Modals fit small screens and slide up from the bottom.

- **📊 Storage Meter**
  - Track storage usage for images, videos, and thumbnails.
  - Refresh metrics from the sidebar at any time.

- **🔁 Import / Export**
  - Backup Vault data to JSON.
  - Restore collections, items, playlists, and notes from JSON.

- **🧠 Zero Configuration SQLite**
  - Uses `vault.db` without manual setup.
  - Works locally or on a private home network.

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
│   ├── pdfs/               # Saved uploaded PDF files
│   └── thumbnails/         # Downloaded link/video thumbnails & favicons
└── templates/
    └── index.html          # Dynamic, responsive frontend UI
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

### 5. Seed Image Workflow
To import local images from the project root, place numbered image files like `1.jpg`, `2.png`, etc. into the `seed_images/` folder. Then click the Scan button in the sidebar or call `POST /api/scan-seed` to auto-import them in numeric order.

### 📱 Mobile Usage
ResourceVault is mobile-friendly and works well on phones and tablets.
- Open the app URL in your phone browser.
- If you host ResourceVault on a public service like Render, use the generated site URL (for example `https://your-app.onrender.com`).
- The app works the same on mobile as on desktop: tap the bottom navigation bar to switch between sections.
- The sidebar is hidden on small screens for a cleaner mobile layout.
- Tap the floating action button (`+`) to add new resources quickly.
- Pull down at the top of any section to refresh the current view.
- Modals slide up from the bottom and resize to fit narrow screens.

---

## 🧭 User Guide

### Main Navigation
- **Desktop:** Use the left sidebar to switch between Links, Videos, Images, PDFs, Collections, Playlists, Notes, Archive, Trash, and Sections.
- **Mobile:** Use the bottom nav bar and floating action button for primary actions.
- **Search:** Toggle the search bar from the topbar to filter cards instantly.
- **Pinned:** Use the pinned filter to surface important resources.

### Adding Resources
- **Links:** Save URL resources with metadata and optional collection assignment.
- **Videos:** Add by URL, upload a file, or paste embed markup.
- **Images:** Upload many images at once and assign chapters or collections.
- **PDFs:** Upload a PDF or add a URL, add tags, and store it in a collection.
- **Collections:** Create collections with cover images and descriptions.
- **Playlists:** Create playlists and add videos from the video gallery.
- **Notes:** Add notes, choose colors, and pin them for quick access.
- **Sections:** Create custom workspace sections for your own categories.

### Workspace Controls
- **Archive:** Keep items safe without cluttering active sections.
- **Trash:** Restore deleted items or delete them permanently.
- **Custom Sections:** Organize custom content types within workspace areas.
- **Selection Mode:** Use multi-select to act on many items at once.
- **Import / Export:** Backup and restore your Vault using the JSON import/export tools.
- **Storage Meter:** Monitor usage for images, videos, and thumbnails.
- **Seed Scan:** Drop files into `seed_images/` and scan to import them.

---

## 🔌 API Reference

ResourceVault exposes a JSON API for all major resource types.

### 🔗 Links API
* **`GET /api/links`** - Returns all saved links.
* **`POST /api/links`** - Save a new link.
  - JSON body: `title`, `url`, `description`, `tags`, `thumbnail`, `collection_id`
* **`DELETE /api/links/<lid>`** - Soft-delete a link (moves it to Trash by setting `trashed=1` and `deleted_at`).

### 🎬 Videos API
* **`GET /api/videos`** - Returns all saved videos.
* **`POST /api/videos`** - Save a new video.
  - Form fields: `type`, `title`, `description`, `tags`, `url`, `file`, `embed_code`, `collection_id`
* **`DELETE /api/videos/<vid>`** - Soft-delete a video.

### 🖼️ Images API
* **`GET /api/images`** - Returns images and triggers seed sync.
* **`POST /api/images`** - Upload images.
  - Form fields: `files`, `tags`, `collection_id`, `chapter_id`
* **`DELETE /api/images/<iid>`** - Soft-delete an image.
* **`POST /api/images/reorder`** - Save image sort order.
* **`POST /api/scan-seed`** - Scan `seed_images/` and import new files.

### 📄 PDFs API
* **`GET /api/pdfs`** - Returns all PDFs.
* **`POST /api/pdfs`** - Save a PDF file or URL.
  - Accepts `multipart/form-data`.
* **`DELETE /api/pdfs/<pid>`** - Soft-delete a PDF.

### 📁 Collections API
* **`GET /api/collections`** - Returns collections.
* **`POST /api/collections`** - Create a collection.
* **`DELETE /api/collections/<cid>`** - Delete a collection.
* **`POST /api/collections/<cid>/items`** - Assign an item to a collection.

### 🧭 Chapters API
* **`GET /api/chapters`** - Returns chapters.
* **`POST /api/chapters`** - Create a chapter.
* **`DELETE /api/chapters/<cid>`** - Delete a chapter.

### 🎧 Playlists API
* **`GET /api/playlists`** - Returns playlists.
* **`POST /api/playlists`** - Create a playlist.
* **`DELETE /api/playlists/<pid>`** - Delete a playlist.
* **`GET /api/playlists/<pid>/items`** - Returns playlist items.
* **`POST /api/playlists/<pid>/items`** - Add a video to a playlist.
* **`DELETE /api/playlists/<pid>/items`** - Remove a playlist item.

### 🗒️ Notes API
* **`GET /api/notes`** - Returns notes.
* **`POST /api/notes`** - Save a note.
* **`PATCH /api/notes/<nid>`** - Update note fields like `title`, `content`, `color`, `tags`, or `pinned`.
* **`DELETE /api/notes/<nid>`** - Soft-delete a note by moving it to Trash.

### 📌 Pin API
* **`PATCH /api/<type>/<id>/pin`** - Toggle `pinned` for `links`, `videos`, `images`, `pdfs`, and `notes`.

### 📊 Storage API
* **`GET /api/storage`** - Returns folder sizes and counts for uploads, images, videos, PDFs, and thumbnails.
* **`DELETE /api/storage/thumbnails`** - Clear all cached thumbnails.

### 🔁 Import / Export API
* **`GET /api/export`** - Export all Vault tables to JSON.
* **`POST /api/import`** - Import Vault data from JSON.

### 🔄 Reorder API
* **`POST /api/<type>/reorder`** - Reorder items by `id` for `links`, `videos`, `pdfs`, `notes`, and `custom_items`.

### 🗃️ Archive & Trash
* **`GET /api/archive`** - Returns archived items.
* **`GET /api/trash`** - Returns trashed items.
* **`PATCH /api/<type>/<id>/restore`** - Restore a trashed item.
* **`DELETE /api/<type>/<id>/permanent`** - Permanently delete an item from the database.
* **`DELETE /api/trash/empty`** - Empty the trash and remove trashed media files.

### 🧩 Custom Sections API
* **`GET /api/custom-sections`** - Returns custom section definitions.
* **`GET /api/custom-items`** - Returns custom section items.
* **`POST /api/custom-sections`** - Create a custom section.
* **`POST /api/custom-items`** - Create a custom item.
* **`PATCH /api/custom-items/<cid>`** - Update a custom item.
* **`DELETE /api/custom-items/<cid>`** - Soft-delete a custom item.

### 📊 Stats API
* **`GET /api/stats`** - Resource counts and storage metrics.

---

## 🗄️ Database Schema

SQLite creates all Vault tables automatically inside `vault.db`:

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
| `collection_id` | TEXT | Optional collection assignment |
| `pinned` | INTEGER | Pin status |
| `trashed` | INTEGER | Soft-delete flag |
| `deleted_at` | DATETIME | Soft-delete timestamp |
| `archived` | INTEGER | Archived flag |
| `sort_order` | INTEGER | Manual sort order |
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
| `collection_id` | TEXT | Optional collection assignment |
| `pinned` | INTEGER | Pin status |
| `trashed` | INTEGER | Soft-delete flag |
| `deleted_at` | DATETIME | Soft-delete timestamp |
| `archived` | INTEGER | Archived flag |
| `sort_order` | INTEGER | Manual sort order |
| `created_at` | DATETIME | Automatic timestamp |

### `images` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Image title (inferred from filename) |
| `filename` | TEXT | Storage name inside uploads/images |
| `sort_order` | INTEGER | Order priority index |
| `tags` | TEXT | Comma-delimited tag list |
| `source` | TEXT | Source flag: `upload` or `seed` |
| `collection_id` | TEXT | Optional collection assignment |
| `chapter_id` | TEXT | Optional image chapter assignment |
| `pinned` | INTEGER | Pin status |
| `trashed` | INTEGER | Soft-delete flag |
| `deleted_at` | DATETIME | Soft-delete timestamp |
| `archived` | INTEGER | Archived flag |
| `created_at` | DATETIME | Automatic timestamp |

### `pdfs` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Display title |
| `type` | TEXT | PDF source: `upload` or `url` |
| `filename` | TEXT | Uploaded PDF filename |
| `url` | TEXT | External PDF URL |
| `description` | TEXT | PDF description |
| `tags` | TEXT | Comma-delimited tag list |
| `collection_id` | TEXT | Optional collection assignment |
| `pinned` | INTEGER | Pin status |
| `trashed` | INTEGER | Soft-delete flag |
| `deleted_at` | DATETIME | Soft-delete timestamp |
| `archived` | INTEGER | Archived flag |
| `sort_order` | INTEGER | Manual sort order |
| `created_at` | DATETIME | Automatic timestamp |

### `collections` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Collection title |
| `description` | TEXT | Collection description |
| `cover_image` | TEXT | Cover image path or URL |
| `type` | TEXT | Collection type |
| `created_at` | DATETIME | Automatic timestamp |

### `chapters` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `collection_id` | TEXT | Parent collection ID |
| `title` | TEXT | Chapter title |
| `sort_order` | INTEGER | Manual sort order |
| `created_at` | DATETIME | Automatic timestamp |

### `playlists` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Playlist title |
| `description` | TEXT | Playlist description |
| `created_at` | DATETIME | Automatic timestamp |

### `playlist_items` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `playlist_id` | TEXT | Parent playlist ID |
| `video_id` | TEXT | Associated video ID |
| `sort_order` | INTEGER | Manual sort order |

### `notes` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Note title |
| `content` | TEXT | Note body |
| `color` | TEXT | Note color |
| `pinned` | INTEGER | Pin status |
| `trashed` | INTEGER | Soft-delete flag |
| `deleted_at` | DATETIME | Soft-delete timestamp |
| `archived` | INTEGER | Archived flag |
| `sort_order` | INTEGER | Manual sort order |
| `tags` | TEXT | Comma-delimited tag list |
| `created_at` | DATETIME | Automatic timestamp |

### `custom_sections` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `title` | TEXT | Section title |
| `icon` | TEXT | Section icon |
| `description` | TEXT | Section description |
| `created_at` | DATETIME | Automatic timestamp |

### `custom_items` Table
| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Unique UUIDv4 string |
| `section_id` | TEXT | Parent section ID |
| `title` | TEXT | Item title |
| `content` | TEXT | Item content |
| `url` | TEXT | Optional URL |
| `filename` | TEXT | Optional filename |
| `type` | TEXT | Item type |
| `tags` | TEXT | Comma-delimited tag list |
| `pinned` | INTEGER | Pin status |
| `trashed` | INTEGER | Soft-delete flag |
| `deleted_at` | DATETIME | Soft-delete timestamp |
| `archived` | INTEGER | Archived flag |
| `sort_order` | INTEGER | Manual sort order |
| `created_at` | DATETIME | Automatic timestamp |

---

## ⚠️ Known Limitations
- Thumbnail fetching may fail on Render free tier due to outbound network restrictions.
- Uploaded video files are large and can quickly exhaust free-tier disk quotas.
- There is no built-in user authentication, so anyone with the URL can access all resources.
- SQLite is single-writer, so concurrent heavy usage may cause lock errors.

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

4. **Host on Render:**
   - Create a new Web Service on Render and connect it to this repository.
   - Set the build command to:
     ```bash
     pip install -r requirements.txt
     ```
   - Set the start command to:
     ```bash
     gunicorn -w 4 -b 0.0.0.0:$PORT app:app
     ```
   - Add any required environment variables in Render, if needed.
   - Warning: Render free tier uses ephemeral storage, so uploaded files and `vault.db` are wiped on every restart or redeploy. Use Render only for testing, link/embed-only usage, or demoing the app without file uploads.
   - For persistent file storage, use a VPS or home server and expose it with Ngrok or a reverse proxy.
   - Once deployed, open the Render-generated URL (for example `https://your-app.onrender.com`) in your phone browser to use ResourceVault from mobile.
