# ⚙️ Automations CLI

A powerful, all-in-one command-line tool built with Python to automate everyday development and file management tasks.

## ✨ Features

* **Project Scaffolding**: Instantly create new Python projects with a standardized directory structure, interactive mode, and flexible options
* **Gist Management**: Upload, update, list, delete, and download GitHub Gists from the command line
* **Database Management**: Automate PostgreSQL database backups and restores
* **Cloud Sync**: Upload database backups directly to any `rclone` remote or Google Drive
* **File Organization**: Clean up directories by sorting files based on their type, extension, date, prefix, or stem
* **System Utilities**: Retrieve saved Wi-Fi passwords, manage WireGuard VPN connections, or automatically install the correct `chromedriver` for your browser
* **Google Photos**: Organize Google Photos Takeout archives
* **Website Cloning**: Clone websites for offline viewing
* **Modular Downloaders**: Download videos, audio, files, and torrents with robust, standalone scripts and consistent CLI options
* **Subtitle Management**: Sync, shift, and embed subtitles into video files

---

## 📂 File Organization

The Automations CLI includes a powerful file organizer tool to help you keep your directories tidy.

### **Default Behavior**

By default, the file organizer will **only organize files in the top-level folder** you specify.  
If you want to organize files in all subfolders as well, use the `--recursive` flag.

### **Usage**

```sh
# Organize only the top-level folder (default)
automations organize-files /path/to/your/folder

# Organize all files in the folder and all subfolders
automations organize-files /path/to/your/folder --recursive

# Use multiple sorting methods and exclude certain files/folders
automations organize-files /path/to/your/folder --method by_type by_date --exclude node_modules .git

# Perform a dry run (see what would happen, but make no changes)
automations organize-files /path/to/your/folder --dry-run

# Enable verbose output for detailed logs
automations organize-files /path/to/your/folder --verbose
```

### **Options**

| Option                | Description                                                                                  | Default                |
|-----------------------|----------------------------------------------------------------------------------------------|------------------------|
| `--method`, `-m`      | Sorting method(s) to use. Can specify multiple. Choices: `by_type`, `by_ext`, `by_date`, `by_prefix`, `by_stem` | `by_type`              |
| `--recursive`, `-r`   | Sort files recursively in all subfolders                                                     | *Not set (top-level only)* |
| `--dry-run`, `-d`     | Perform a dry run without actually moving files                                              | *Not set*              |
| `--verbose`, `-v`     | Enable verbose output                                                                        | *Not set*              |
| `--exclude`           | Files or folders to exclude from organization. Can specify multiple.                         | *None*                 |

**Note:**  
- The `--recursive` flag is now the only way to process subfolders.  
- The `--simple` flag has been removed; "simple" (top-level only) is now the default.

---

## 📥 Downloaders

Automations CLI provides robust, modular downloaders for:

- **Video**: Download videos from URLs or playlists using yt-dlp, with advanced playlist and quality options.
- **Audio**: Download audio (as mp3) from video URLs or playlists, with the same playlist handling as video.
- **File**: Download any file (ebooks, images, etc.) using wget or curl, with resume and quiet mode support.
- **Torrent**: Download torrents or magnet links using aria2c, with pause/resume, speed limits, and config file support.

All downloaders are invoked via the unified `automations download` command and support config files for defaults.

#### **Examples**

```sh
# Download a video
automations download video "https://youtube.com/..."

# Download audio from a playlist
automations download audio "https://youtube.com/..." --playlist-mode all

# Download a file
automations download file "https://example.com/file.pdf"

# Download a torrent (magnet link)
automations download torrent "magnet:?xt=urn:btih:..."

# Download a torrent with pause/resume support
automations download torrent "magnet:?..." --session ~/.aria2.session
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
    * `rclone`
    * `exiftool`
    * `pg_dump` & `pg_restore`
    * `yt-dlp`
    * `ffmpeg` (for subtitle and video operations)
    * `aria2c` (for torrent downloads)
    * `wget` and/or `curl` (for file downloads)

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

* **Downloaders**:
  - Each downloader supports its own config file for default options (e.g., output directory, speed limits, session file for torrents).
  - See `~/.torrent_downloader_config.ini` and similar for details.

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
| `clone-website`      | Clones a website for offline viewing                                        |
| `download video`     | Download videos from URLs or playlists using yt-dlp                         |
| `download audio`     | Download audio (mp3) from video URLs or playlists                           |
| `download file`      | Download any file using wget or curl, with resume support                   |
| `download torrent`   | Download torrents or magnet links using aria2c, with pause/resume support   |
| `generate-docs`      | Generates project documentation files (README.md, LICENSE,...)              |
| `generate-project`   | Generates a new project directory structure (with interactive mode)         |
| `get-wifi-passwords` | Retrieves known Wi-Fi SSIDs and passwords                                   |
| `install-chromedriver` | Downloads and installs the correct ChromeDriver                           |
| `organize-files`     | Organizes files into subfolders based on extension, type, date, etc.        |
| `pg-backup`          | PostgreSQL Backup/Restore Tool with Cloud Upload                            |
| `process-takeout`    | Organizes a Google Photos Takeout archive                                   |
| `run-wireguard`      | Interactive tool to activate and manage WireGuard VPN connections           |
| `subtitle`           | Tools for shifting, syncing, and embedding subtitles                        |
| `gist`               | Tools for managing GitHub Gists (upload, update, list, delete, download)    |

---

## 🧑‍💻 Interactive Mode

You can use `--interactive` with `generate-project` to be prompted for all options, making it easy to scaffold a new project without remembering flags.

```sh
automations generate-project --interactive
```

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

* **Update an existing gist:**
  ```sh
  automations gist update myscript.py --update <gist_id>
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
