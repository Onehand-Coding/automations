import sys
import typer
import subprocess
from pathlib import Path
from typing import Optional, List

# The main Typer application
app = typer.Typer(
    name="automations",
    help="🤖 A CLI for running your personal automation scripts.",
    rich_markup_mode="markdown",
    no_args_is_help=True,
)


# --- Helper Function to Run Scripts ---
def _run_script(script_name: str, args: list[str] = [], use_sudo: bool = False):
    """Finds and runs a script from the 'commands' directory."""
    python_executable = sys.executable
    cli_dir = Path(__file__).parent
    script_path = cli_dir / "commands" / script_name

    if not script_path.exists():
        typer.secho(
            f"Error: Script '{script_name}' not found at '{script_path}'",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    command = [python_executable, str(script_path)] + args
    if use_sudo:
        command.insert(0, "sudo")
        typer.secho(
            "🔒 This command requires sudo. Prompting for password...",
            fg=typer.colors.YELLOW,
        )

    typer.echo(f"▶️  Running: {' '.join(command)}")
    # We use .call here instead of .run to allow the script to be interactive (e.g., for password prompts)
    subprocess.call(command)


# --- CLI Commands ---


@app.command()
def generate_project(
    project_name: str = typer.Argument(
        ..., help="The name for the new project directory."
    ),
):
    """Generates a new project directory structure."""
    _run_script("project_generator.py", [project_name])


@app.command()
def organize_files(
    directory: str = typer.Argument(
        ".", help="The directory to organize. Defaults to current."
    ),
):
    """Organizes files into subfolders based on extension."""
    _run_script("file_organizer.py", [directory])


@app.command()
def process_takeout(
    source: str = typer.Option(
        ..., "--source", help="Source directory of the Google Photos Takeout."
    ),
    dest: str = typer.Option(
        ..., "--dest", help="Destination directory to organize photos into."
    ),
):
    """Organizes a Google Photos Takeout archive."""
    _run_script("gphotos_takeout_organizer.py", ["--source", source, "--dest", dest])


@app.command()
def clone_website(
    url: str = typer.Argument(..., help="The URL of the website to clone."),
    output_dir: Optional[str] = typer.Argument(None, help="Optional output directory."),
):
    """Clones a website for offline viewing."""
    args = [url]
    if output_dir:
        args.append(output_dir)
    _run_script("website_cloner.py", args)


@app.command()
def get_wifi_passwords():
    """Retrieves known Wi-Fi SSIDs and passwords from the system."""
    _run_script("wayfay.py")


@app.command()
def install_chromedriver(
    browser: str = typer.Option(
        "brave", help="Browser to detect: 'chrome', 'brave', or 'chromium'."
    ),
    force: bool = typer.Option(
        False, "--force", help="Force installation even if already installed."
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
):
    """
    Downloads and installs the correct ChromeDriver for your browser version.
    **NOTE: This command requires sudo/root privileges to run.**
    """
    args = ["--browser", browser]
    if force:
        args.append("--force")
    if debug:
        args.append("--debug")
    _run_script("install_chromedriver.py", args, use_sudo=True)


@app.command()
def run_wireguard(
    log_level: str = typer.Option(
        "INFO", "--log-level", help="Set logging level: DEBUG, INFO, WARNING, ERROR."
    ),
):
    """
    An interactive tool to activate and manage WireGuard configurations.
    **NOTE: This command requires sudo/root privileges to run.**
    """
    _run_script("wg_activate.py", ["--log-level", log_level], use_sudo=True)


@app.command()
def pg_backup(
    action: str = typer.Argument(
        ..., help="Action to perform: 'backup', 'restore', or 'list'."
    ),
    db_url: Optional[str] = typer.Option(
        None, "--db-url", help="Database connection string/URL."
    ),
    backup_file: Optional[str] = typer.Option(
        None, "--backup-file", help="Specific backup file to restore."
    ),
    backup_dir: Optional[str] = typer.Option(
        None, "--backup-dir", help="Directory to store/find local backups."
    ),
    upload: bool = typer.Option(
        False, "--upload", help="Upload backup to the cloud after creation."
    ),
    upload_method: str = typer.Option(
        "rclone", "--upload-method", help="Cloud upload method: 'rclone' or 'gdrive'."
    ),
    rclone_remote: Optional[str] = typer.Option(
        None, "--rclone-remote", help="Name of the configured rclone remote."
    ),
    rclone_target_dir: Optional[str] = typer.Option(
        None, "--rclone-target-dir", help="Target directory on the rclone remote."
    ),
):
    """PostgreSQL Backup/Restore Tool with Cloud Upload."""
    args = [action]
    if db_url:
        args.extend(["--db-url", db_url])
    if backup_file:
        args.extend(["--backup-file", backup_file])
    if backup_dir:
        args.extend(["--backup-dir", backup_dir])
    if upload:
        args.append("--upload")
    if upload_method:
        args.extend(["--upload-method", upload_method])
    if rclone_remote:
        args.extend(["--rclone-remote", rclone_remote])
    if rclone_target_dir:
        args.extend(["--rclone-target-dir", rclone_target_dir])

    _run_script("pg_backup_tool.py", args)


@app.command()
def download_video(
    url: Optional[str] = typer.Argument(
        None, help="The URL of the video to download or list formats for."
    ),
    output_name: Optional[str] = typer.Argument(None, help="Optional output filename."),
    quality: Optional[str] = typer.Option(
        "best",
        "--quality",
        "-q",
        help="Set video quality (e.g., '1080p', '720p', 'best').",
    ),
    list_formats: bool = typer.Option(
        False,
        "--list-formats",
        "-l",
        help="List available formats for the URL instead of downloading.",
    ),
    playlist_mode: str = typer.Option(
        "download_all",
        "--playlist-mode",
        "-p",
        help="Playlist handling: download_all, single, first_n, audio_only.",
    ),
    items: Optional[str] = typer.Option(
        None,
        "--items",
        "-i",
        help="Download specific items from a playlist (e.g., '5', '2-4,8'). Works with --playlist-mode audio_only.",
    ),
    create_config: bool = typer.Option(
        False, "--create-config", help="Create a default configuration file and exit."
    ),
    no_config: bool = typer.Option(
        False, "--no-config", help="Run without loading settings from the config file."
    ),
    browser: Optional[str] = typer.Option(
        None,
        "--browser",
        "-b",
        help="Browser to use for cookies (brave, chrome, firefox, etc.).",
    ),
    archive: Optional[Path] = typer.Option(
        None,
        "--archive",
        help="Path to a download archive file to record downloaded files.",
    ),
):
    """
    Downloads video or audio from a URL using yt-dlp, with advanced options.
    """
    args = []

    # Handle standalone commands first
    if create_config:
        args.append("--create-config")
        _run_script("video_downloader.py", args)
        return

    # A URL is required for any other action
    if not url:
        print("❌ Error: A URL is required unless using '--create-config'.")
        raise typer.Exit(1)

    args.append(url)

    if list_formats:
        args.append("--list-formats")
        _run_script("video_downloader.py", args)
        return

    # For downloads, add the remaining arguments
    if output_name:
        args.append(output_name)

    args.extend(["--quality", quality])
    args.extend(["--playlist-mode", playlist_mode])

    if no_config:
        args.append("--no-config")

    if items:
        args.extend(["--items", items])

    if browser:
        args.extend(["--browser", browser])

    if archive:
        args.extend(["--archive", str(archive)])

    _run_script("video_downloader.py", args)


if __name__ == "__main__":
    app()
