# ⚙️ Automations CLI

A powerful, all-in-one command-line tool built with Python to automate everyday development and file management tasks.

## ✨ Features

* **Project Scaffolding**: Instantly create new Python projects with a standardized directory structure
* **Database Management**: Automate PostgreSQL database backups and restores
* **Cloud Sync**: Upload database backups directly to any `rclone` remote or Google Drive
* **File Organization**: Clean up directories by sorting files based on their type and name
* **System Utilities**: Retrieve saved Wi-Fi passwords, manage WireGuard VPN connections, or automatically install the correct `chromedriver` for your browser
* **Google Photos**: Organize Google Photos Takeout archives
* **Website Cloning**: Clone websites for offline viewing
* **Wayfay Integration**: Custom workflow automation

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

**Steps:**

1. **Clone the repository:**

   ```sh
   git clone https://github.com/Phoenix1025/automations.git
   cd automations
   ```

2. **Create and activate a virtual environment:**

   ```sh
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the tool:**
   This command uses `pyproject.toml` to install the tool and all its dependencies, making the `automations` command available.

   ```sh
   uv pip install -e .
   ```

## 🛠️ Configuration

For commands that require credentials or specific paths, create a `.env` file in the project's root directory.

* **PostgreSQL Backups (`pg-backup`)**:
  ```env
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

## 📋 Usage

All functionality is accessed through the main `automations` command.

```sh
# See a list of all available commands
automations --help
```

### Commands Overview

| Command | Description |
|---------|-------------|
| `project-generator` | Scaffolds a new Python project directory |
| `pg-backup` | Backs up, restores, or lists PostgreSQL database dumps |
| `file-organizer` | Sorts files in a directory into subfolders |
| `gphotos-takeout-organizer` | Organizes a Google Photos Takeout archive |
| `install-chromedriver` | Installs the correct `chromedriver` for your browser |
| `wg-activate` | Interactively manage WireGuard VPN connections |
| `wayfay` | Custom workflow automation |
| `website-cloner` | Clones a website for offline viewing |

### Command Examples

* **Create a new project:**
  ```sh
  automations project-generator my-new-app
  ```

* **Backup a database and upload it:**
  ```sh
  automations pg-backup backup --upload --upload-method rclone
  ```

* **Restore the latest backup from the cloud:**
  ```sh
  # This will prompt you to download the latest backup from your rclone remote
  automations pg-backup restore
  ```

* **Install ChromeDriver automatically (requires sudo):**
  ```sh
  automations install-chromedriver
  ```

* **Organize your Downloads folder:**
  ```sh
  automations file-organizer ~/Downloads
  ```

* **Organize Google Photos Takeout:**
  ```sh
  automations gphotos-takeout-organizer /path/to/takeout-archive
  ```

* **Manage WireGuard connections:**
  ```sh
  automations wg-activate
  ```

* **Clone a website:**
  ```sh
  automations website-cloner https://example.com
  ```

## 📁 Project Structure

```
automations/
├── automations_cli/           # Main package
│   ├── commands/             # Command implementations
│   │   ├── helper/          # Shared utilities
│   │   │   ├── configs.py   # Configuration helpers
│   │   │   └── funcs.py     # Common functions
│   │   ├── file_organizer.py
│   │   ├── gphotos_takeout_organizer.py
│   │   ├── install_chromedriver.py
│   │   ├── pg_backup_tool.py
│   │   ├── project_generator.py
│   │   ├── wayfay.py
│   │   ├── website_cloner.py
│   │   └── wg_activate.py
│   └── main.py              # CLI entry point
├── data/                    # Application data
│   ├── backup-tool/         # Database backups & credentials
│   └── wifi_passwords.json  # Stored Wi-Fi passwords
├── logs/                    # Application logs
├── pyproject.toml          # Project configuration
├── requirements.txt        # Python dependencies
└── uv.lock                # UV lock file
```

## 🔧 Development

To contribute or modify the tool:

1. **Fork and clone the repository**
2. **Set up the development environment:**
   ```sh
   uv venv
   source .venv/bin/activate
   uv pip install -e .
   ```
3. **Make your changes** in the `automations_cli/` directory
4. **Test your changes** by running the CLI commands
5. **Submit a pull request**

## 🤝 Contributing

This repository is primarily for personal learning and utility. However, suggestions or improvements are welcome. Feel free to open an issue or submit a pull request.
