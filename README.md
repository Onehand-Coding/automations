# ⚙️ Automations CLI

A powerful, all-in-one command-line tool built with Python to automate everyday development and file management tasks.

## ✨ Features

* **Project Scaffolding**: Instantly create new Python projects with a standardized directory structure, interactive mode, and flexible options
* **Gist Management**: Upload, update, list, delete, and download GitHub Gists from the command line
* **Database Management**: Automate PostgreSQL database backups and restores
* **Cloud Sync**: Upload database backups directly to any `rclone` remote or Google Drive
* **File Organization**: Clean up directories by sorting files based on their type and name
* **System Utilities**: Retrieve saved Wi-Fi passwords, manage WireGuard VPN connections, or automatically install the correct `chromedriver` for your browser
* **Google Photos**: Organize Google Photos Takeout archives
* **Website Cloning**: Clone websites for offline viewing
* **Video Downloading**: Download videos or audio from URLs using yt-dlp with advanced options
* **Subtitle Management**: Sync, shift, and embed subtitles into video files

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
| `download-video`     | Downloads video or audio from a URL using yt-dlp                            |
|generate-docs         |Generates project documentation files (README.md, LICENSE,..)                |
| `generate-project`   | Generates a new project directory structure (with interactive mode)         |
| `get-wifi-passwords` | Retrieves known Wi-Fi SSIDs and passwords                                   |
| `install-chromedriver` | Downloads and installs the correct ChromeDriver                           |
| `organize-files`     | Organizes files into subfolders based on extension                          |
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

## 🛠️ Project Generator Examples

* **Create a new project interactively:**
  ```sh
  automations generate-project --interactive
  ```

* **Create a new project without docs:**
  ```sh
  automations generate-project myproject --no-docs
  ```

* **Create a CLI tool project:**
  ```sh
  automations generate-project mycli --type cli
  ```

---

## 🗂️ Project Structure

```
automations/
├── src/                     # Source code
│   │
│   └── automations_cli/     # Main package
│       ├── __init__.py
│       ├── main.py          # CLI entry point
│       ├── helper/          # Shared utilities
│       │   ├── __init__.py
│       │   ├── configs.py   # Configuration helpers
│       │   ├── funcs.py     # Common functions
│       │   └── templates.py # Template utilities
│       ├── docs_generator.py
│       ├── file_organizer.py
│       ├── gist_manager.py
│       ├── gphotos_takeout_organizer.py
│       ├── install_chromedriver.py
│       ├── pg_backup_tool.py
│       ├── project_generator.py
│       ├── subtitle_manager.py
│       ├── video_downloader.py
│       ├── wayfay.py
│       ├── website_cloner.py
│       └── wg_activate.py
├── data/                    # Application data
│   ├── backup-tool/         # Database backups & credentials
│   │   ├── credentials.json
│   │   ├── token.pickle
│   │   └── db/              # Database backup files
│   │       ├── db_backup_20250510_093801.dump
│   │       ├── db_backup_20250518_070156.dump
│   │       └── db_backup_20250704_165920.dump
│   └── wifi_passwords.json  # Stored Wi-Fi passwords
├── logs/                    # Application logs
│   ├── backup_tool.log
│   ├── chromedriver_installer.log
│   ├── docs_generator.log
│   ├── file_organizer.log
│   ├── gist_uploader.log
│   ├── project_generator.log
│   ├── subtitle_manager.log
│   ├── video_downloader.log
│   └── wireguard_activator_.log
├── pyproject.toml          # Project configuration
├── README.md               # Project documentation
└── uv.lock                 # UV lock file
```

---

## 🔧 Development

To contribute or modify the tool:

1. **Fork and clone the repository**
2. **Set up the development environment:**
   ```sh
   uv sync

   # or

   uv venv
   source .venv/bin/activate
   uv pip install -e .
   ```
3. **Make your changes** in the `automations_cli/` directory
4. **Test your changes** by running the CLI commands
5. **Submit a pull request**

---

## 🤝 Contributing

This repository is primarily for personal learning and utility. However, suggestions or improvements are welcome. Feel free to open an issue or submit a pull request.
