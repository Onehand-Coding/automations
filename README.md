# ⚙️ Automations CLI

A powerful, all-in-one command-line tool built with Python to automate everyday development and file management tasks.

## ✨ Features

* **Project Scaffolding**: Instantly create new Python projects with standardized directory structure (app, CLI, library), interactive mode, fullstack projects (FastAPI + React), and flexible options
* **Documentation Generation**: Generate project documentation files (README.md, LICENSE, pyproject.toml, .gitignore) with customizable templates
* **File Organization**: Clean up directories by sorting files based on their type, extension, date, or name with recursive and dry-run options
* **File Downloading**: Download files using aria2c, wget, or curl with resume support and multiple method fallbacks
* **Video/Audio Downloading**: Download videos, audio, and playlists from various platforms using yt-dlp with quality options, format listing, and browser cookie integration
* **Torrent Downloading**: Download torrents or magnet links using aria2c with pause/resume, speed limits, seeding options, and session file support
* **Gist Management**: Upload, update, list, delete, and download GitHub Gists from the command line with interactive mode
* **Subtitle Management**: Automatically sync subtitles with videos using audio analysis, shift time in subtitle files, or embed subtitles into videos (softsub or hardsub)
* **Database Management**: Automate PostgreSQL database backups and restores with cloud upload support (rclone or Google Drive)
* **Google Photos Organization**: Organize Google Photos Takeout archives by embedding metadata from JSON files into media files
* **Website Cloning**: Clone entire websites for offline viewing using HTTrack
* **System Utilities**: Retrieve saved Wi-Fi passwords, manage WireGuard VPN connections, or automatically install the correct `chromedriver` for your browser

---

## 📂 File Organization

The Automations CLI includes a powerful file organizer tool to help you keep your directories tidy.

### **Default Behavior**

By default, the file organizer will **only organize files in the top-level folder** you specify.  
If you want to organize files in all subfolders as well, use the `--recursive` flag.

### **Usage**

```sh
# Organize only the top-level folder by type (default)
automations organize-files /path/to/your/folder

# Organize all files in the folder and all subfolders
automations organize-files /path/to/your/folder --recursive

# Use multiple sorting methods and exclude certain files/folders
automations organize-files /path/to/your/folder --method type date --exclude node_modules .git

# Perform a dry run (see what would happen, but make no changes)
automations organize-files /path/to/your/folder --dry-run

# Enable verbose output for detailed logs
automations organize-files /path/to/your/folder --verbose
```

### **Options**

| Option                | Description                                                                                  | Default                |
|-----------------------|----------------------------------------------------------------------------------------------|------------------------|
| `--method`, `-m`      | Sorting method(s) to use. Can specify multiple. Choices: `type`, `extension`, `date`, `name` | `type`              |
| `--recursive`, `-r`   | Sort files recursively in all subfolders                                                     | *Not set (top-level only)* |
| `--dry-run`, `-d`     | Perform a dry run without actually moving files                                              | *Not set*              |
| `--verbose`, `-v`     | Enable verbose output                                                                        | *Not set*              |
| `--exclude`           | Files or folders to exclude from organization. Can specify multiple.                         | *None*                 |

---

## 📥 Downloaders

Automations CLI provides robust, modular downloaders for:

- **Video**: Download videos from URLs or playlists using yt-dlp, with quality options, format listing, browser cookies, download archives, and advanced playlist handling (all items, specific items).
- **Audio**: Download audio (as mp3) from video URLs or playlists, with the same playlist handling as video.
- **File**: Download any file (ebooks, images, etc.) using aria2c (with progress), wget, or curl with resume support and multiple method fallbacks.
- **Torrent**: Download torrents or magnet links using aria2c, with pause/resume, speed limits, seeding options, config file support, and session file management.

All downloaders are invoked via the unified `automations download` command and support config files for defaults.

#### **Examples**

```sh
# Download a video
automations download video "https://youtube.com/..."

# Download video in specific quality
automations download video "https://youtube.com/..." --quality 1080p

# Download audio from a playlist
automations download audio "https://youtube.com/..." --playlist-mode all

# List available formats for a video
automations download video "https://youtube.com/..." --list-formats

# Download a file using specific method
automations download file "https://example.com/file.pdf" --method aria2

# Download a torrent (magnet link)
automations download torrent "magnet:?xt=urn:btih:..."

# Download a torrent with upload limit
automations download torrent "magnet:?..." --max-upload 500K

# Download specific items from a playlist
automations download video "https://youtube.com/playlist?list=..." --playlist-mode items --items "1-5,8,10"
```

See `automations download <type> --help` for all options.

---

## 🚀 Installation

This tool is designed to be installed and run from a dedicated Python virtual environment using `uv`.

**Prerequisites:**

* Python 3.9+
* `git`
* [uv](https://github.com/astral-sh/uv) (recommended)
* External Tools (for certain commands):
    * `rclone` (for cloud uploads in pg-backup)
    * `exiftool` (for Google Photos Takeout organization)
    * `pg_dump` & `pg_restore` (for PostgreSQL backup/restore)
    * `yt-dlp` (for video/audio downloads)
    * `ffmpeg` (for subtitle operations and video processing)
    * `ffsubsync` (for automatic subtitle synchronization)
    * `aria2c` (for torrent and advanced file downloads)
    * `wget` and/or `curl` (for basic file downloads)
    * `HTTrack` (for website cloning)
    * `chromedriver` (for browser automation - automatically installed with install-chromedriver command)

**Steps:**

1. **Clone the repository:**

   ```sh
   git clone https://github.com/Phoenix1025/automations.git
   cd automations
   ```

2. **Create, activate a virtual environment and Install the tool:**
   This command uses `pyproject.toml` to install the tool and all its dependencies, making the `automations` command available.

   ```sh
   uv sync # All at once

   # or

   uv venv

   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   uv pip install -e .
   ```

---

## 🛠️ Configuration

For commands that require credentials or specific paths, create a `.env` file in the project's root directory.

* **PostgreSQL Backups (`pg-backup`)**:
  ```env
  # === pg backup ===

  # Your database connection string
  DB_URL="postgresql://user:password@host:port/dbname"

  # rclone remote name for uploads
  RCLONE_REMOTE_NAME="MyGdrive"

  # Email notification settings (optional)
  EMAIL_FROM="your-email@example.com"
  EMAIL_TO="recipient@example.com"
  SMTP_SERVER="smtp.example.com"
  SMTP_PORT="587"
  SMTP_USERNAME="your-username"
  SMTP_PASSWORD="your-app-password"
  ```

* **Google Drive API**:
  For the `pg-backup` command to use the `gdrive` upload method, place your `credentials.json` file (from Google Cloud Console) in the `data/backup-tool/` directory.

* **GitHub Gist Management**:
  For all `gist` commands, set your GitHub token in a `.env` file or in `~/.gist`:
  ```env
  GITHUB_TOKEN=your_github_token
  ```

* **Downloaders Configuration**:
  - Each downloader supports its own config file for default options (output directory, speed limits, session file for torrents, etc.)
  - Video/Audio: `~/.config/automations/.video_downloader_config.ini`
  - Torrents: `~/.config/automations/.torrent_downloader_config.ini`
  - Configs are created automatically with default values

* **Google Photos Takeout Organizer**:
  Requires `exiftool` to be installed and available in system PATH for metadata embedding

---

## 📋 Usage

All functionality is accessed through the main `automations` command.

```sh
# See a list of all available commands
automations --help
```

### Commands Overview

| Command              | Description                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `clone-website`      | Clones a website for offline viewing using HTTrack                          |
| `download video`     | Download videos from URLs or playlists using yt-dlp with quality options and format listing |
| `download audio`     | Download audio (mp3) from video URLs or playlists, with browser cookie support |
| `download file`      | Download any file using aria2c, wget or curl with resume and quiet mode support |
| `download torrent`   | Download torrents or magnet links using aria2c, with pause/resume, speed limits, seeding options |
| `generate-docs`      | Generates project documentation files (README.md, LICENSE, pyproject.toml, .gitignore) |
| `generate-project`   | Generates a new project with flexible templates (app/cli/lib), interactive mode, or fullstack (FastAPI + React) |
| `get-wifi-passwords` | Retrieves known Wi-Fi SSIDs and passwords on your system                    |
| `install-chromedriver` | Downloads and installs the correct ChromeDriver for your browser version (requires sudo) |
| `organize-files`     | Organizes files into subfolders based on extension, type, date, or name with recursive and dry-run options |
| `pg-backup`          | PostgreSQL Backup/Restore Tool with Cloud Upload (rclone or Google Drive) and email notifications (requires sudo) |
| `process-takeout`    | Organizes a Google Photos Takeout archive by embedding metadata from JSON files |
| `run-wireguard`      | Interactive tool to activate and manage WireGuard VPN connections (requires sudo) |
| `subtitle`           | Tools for shifting, syncing (using audio analysis), and embedding subtitles (softsub/hardsub) |
| `gist`               | Tools for managing GitHub Gists (upload, update, list, delete, download)    |

---

## 🧑‍💻 Interactive Mode

You can use `--interactive` with `generate-project` to be prompted for all options, making it easy to scaffold a new project without remembering flags.

```sh
automations generate-project --interactive
```

## 🌐 Fullstack Project Generation

The project generator includes a special feature to create fullstack applications with a FastAPI backend and React frontend:

```sh
# Create a fullstack project (FastAPI + React)
automations generate-project my-fullstack-app --fullstack
```

This generates a complete project structure with:
- Backend: FastAPI with SQLAlchemy, Pydantic, and proper project structure
- Frontend: React with Vite, including proxy configuration for API requests
- Proper configuration files for both backend and frontend
- Complete README with setup instructions

---

## 📝 Gist Management

Manage your GitHub Gists directly from the CLI:

* **List your gists:**
  ```sh
  automations gist list
  ```

* **Upload a file as a new gist:**
  ```sh
  automations gist upload myscript.py --description "My script"
  ```

* **Update an existing gist by ID or filename:**
  ```sh
  automations gist update <gist_id> myscript.py --description "Updated script"
  ```

* **Update only the description of a gist:**
  ```sh
  automations gist update <gist_id> --description "New description" --description-only
  ```

* **Delete a gist:**
  ```sh
  automations gist delete <gist_id>
  ```

* **Download a gist by ID or URL:**
  ```sh
  automations gist download <gist_id>
  automations gist download <gist_id> --output-dir ~/Downloads
  automations gist download https://gist.github.com/username/<gist_id>
  ```

## 🎞️ Subtitle Management

The automation includes powerful subtitle tools for various operations:

* **Automatically sync subtitles to video using audio analysis:**
  ```sh
  automations subtitle sync video.mp4 unsynced.srt synced.srt
  ```

* **Shift subtitles by a specific time offset:**
  ```sh
  automations subtitle shift original.srt shifted.srt --offset -2.5
  ```

* **Embed subtitles into a video file (softsub by default):**
  ```sh
  automations subtitle embed video.mp4 subs.srt output.mp4
  ```

* **Embed subtitles permanently (hardsub):**
  ```sh
  automations subtitle embed video.mp4 subs.srt output.mp4 --hard
  ```

---

## 📄 Documentation Generation

Generate project documentation files with customizable templates:

```sh
# Generate all documentation files (README, LICENSE, pyproject.toml, .gitignore)
automations generate-docs --all --project-name "my-project" --description "My awesome project"

# Generate specific files
automations generate-docs --readme --license --project-name "my-project"

# Generate in specific directory
automations generate-docs --all --dir ./my-project --project-name "my-project"
```

---
## 📑 License

MIT License

---

## 🙋‍♂️ Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## 🗒️ Notes

- This project is under active development and is tailored for personal automation needs.
- Some features require external tools to be installed and available in your system PATH.
- For any issues or feature requests, please open an issue on GitHub.

---
