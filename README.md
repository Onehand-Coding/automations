# Personal Automation Scripts

This repository contains a collection of Python scripts designed to automate various tasks. These were developed as practice exercises and utility tools.

## Overview

The goal of this project is to explore different aspects of Python programming by creating practical automation solutions for everyday tasks, ranging from file management and backups to development workflow enhancements.

## Scripts Included

Here's a breakdown of the main scripts available in the `scripts/` directory:

### 1. PostgreSQL Backup Tool (`pg_backup_tool.py`)

* **Purpose:** Automates the backup and restore process for PostgreSQL databases.
* **Features:**
    * Creates PostgreSQL database dumps (`pg_dump`).
    * Restores databases from dump files (`pg_restore`).
    * Supports uploading backups to cloud storage using:
        * **rclone** (Default): Uploads to any rclone-configured remote (e.g., Google Drive, S3, etc.). Requires rclone to be installed and configured.
        * **Google Drive API**: Uploads directly to Google Drive. Requires Google Cloud credentials (`credentials.json`) and initial OAuth2 authentication.
    * Finds and downloads the latest backup from an rclone remote for restoration.
    * Sends email notifications for backup/restore success or failure.
    * Configurable via command-line arguments and `.env` file.
* **Usage:** Run from the command line, specifying an action (`backup`, `restore`, `list`) and other options. Example:
    ```bash
    python scripts/pg_backup_tool.py backup --upload --upload-method rclone --rclone-remote MyGdriveRemote
    python scripts/pg_backup_tool.py restore --db-url <your_restore_db_url>
    python scripts/pg_backup_tool.py restore --backup-file data/pg_backups/db/db_backup_YYYYMMDD_HHMMSS.dump
    ```

### 2. Google Photos Takeout Organizer (`gphotos_takeout_organizer.py`)

* **Purpose:** Processes extracted Google Photos Takeout archives, embedding metadata from JSON sidecar files into the corresponding image/video files.
* **Features:**
    * Recursively finds media files (JPG, PNG, MP4, MOV, etc.) and their matching JSON files within the Takeout structure.
    * Uses `exiftool` (must be installed separately) to embed metadata (like timestamps, descriptions, locations) from the JSON into the media files.
    * Handles various Google Photos naming conventions (e.g., `(edited)`, `(#)` suffixes).
    * Optionally deletes JSON files after successful metadata embedding.
    * Includes dry-run mode and verbose logging.
* **Usage:**
    ```bash
    # Ensure exiftool is installed
    python scripts/gphotos_takeout_organizer.py /path/to/google-photos-takeout --delete-json --verbose
    python scripts/gphotos_takeout_organizer.py /path/to/takeout --dry-run
    ```

### 3. File Organizer (`file_organizer.py`)

* **Purpose:** Sorts files within a specified directory based on various criteria.
* **Features:**
    * **Simple Sort:** Organizes files into subfolders based on their file extension (e.g., `.jpg`, `.pdf`) and then optionally by the first word (prefix) in their filename.
    * **Aggressive Sort:** A more complex sort that organizes by file type (Video, Audio, Image, etc.), then by extension, then attempts to group files by common prefixes and common word sequences (stems) in their filenames.
    * Moves empty folders to the system trash after sorting (for Aggressive sort).
    * Uses a `helper` module for common functions.
* **Usage:**
    ```bash
    python scripts/file_organizer.py
    # Follow prompts to select directory and sort type (Simple/Aggressive)
    ```

### 4. Python Project Generator (`project_generator.py`)

* **Purpose:** Quickly scaffolds a new Python project structure.
* **Features:**
    * Creates a standard project layout including a main package directory, `__init__.py`, `main.py`, `setup.py`, `README.md`, `.gitignore`, and an empty `requirements.txt`.
    * Initializes a Git repository with an initial commit.
    * Creates a Python virtual environment (`.venv`).
    * Generates a basic `.sublime-project` file with LSP settings (optional).
    * Optionally opens the created project in Sublime Text.
* **Usage:**
    ```bash
    python scripts/project_generator.py --name my-new-project --path /path/to/projects --open
    python scripts/project_generator.py # Interactive mode
    ```

### 5. WiFi Password Retriever (`wayfay.py`)

* **Purpose:** Retrieves and displays saved WiFi network SSIDs and their passwords from the system (requires administrative privileges on some OS).
* **Features:**
    * Supports Windows (`netsh`), macOS (`security`), and Linux (`nmcli` or NetworkManager files).
    * Extracts SSIDs and attempts to retrieve corresponding passwords.
    * Saves the retrieved information to `scripts/data/wifi_passwords.json`.
* **Usage:**
    ```bash
    # May need to run with sudo on Linux/macOS for password access
    python scripts/wayfay.py
    ```

### Helper Module (`helper/funcs.py`)

* Contains common utility functions used by other scripts, such as user confirmation prompts, path handling, JSON/CSV operations, and logging configuration.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Phoenix1025/automations.git
    cd automations
    ```
2.  **Create and activate a virtual environment:** (Recommended)
    ```bash
    python -m venv .venv
    # On Windows:
    # .venv\Scripts\activate
    # On Linux/macOS:
    # source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Install External Tools (if needed):**
    * **rclone:** Required for the `rclone` upload method in `pg_backup_tool.py`. Follow instructions at [rclone.org](https://rclone.org/install/).
    * **exiftool:** Required for `gphotos_takeout_organizer.py`. Follow instructions at [exiftool.org](https://exiftool.org/install.html).
    * **PostgreSQL Client Tools:** `pg_dump` and `pg_restore` are required for `pg_backup_tool.py`. Install the PostgreSQL client utilities appropriate for your operating system.
5.  **Configuration:**
    * **`pg_backup_tool.py`:** Create a `.env` file in the `automations` root directory to store database URLs, email settings, and default rclone remote names. See the script for environment variables used (e.g., `DB_URL`, `EMAIL_FROM`, `SMTP_PASSWORD`, `RCLONE_REMOTE_NAME`).
    * **Google Drive Upload (`pg_backup_tool.py`)**: Place your `credentials.json` file (from Google Cloud Console) inside the `scripts/` directory. Run the script once with `--upload-method gdrive` to perform the initial OAuth authentication.

## Contributing

This repository is primarily for personal learning and utility. However, suggestions or improvements are welcome. Feel free to open an issue or submit a pull request.
