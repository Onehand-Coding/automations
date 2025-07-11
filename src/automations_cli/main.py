#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
from typing import Optional, List

import typer

# The main Typer application
app = typer.Typer(
    name="automations",
    help="🤖 A CLI for running your personal automation scripts.",
    rich_markup_mode="markdown",
    no_args_is_help=True,
)

# Dedicated Typer app for the subtitle commands
subtitle_app = typer.Typer(
    name="subtitle", help="Tools for shifting and embedding subtitles."
)

# Dedicated Typer app for gist commands
gist_app = typer.Typer(name="gist", help="Tools for managing GitHub gists.")

# Add dedicated apps to main app
app.add_typer(subtitle_app)
app.add_typer(gist_app)


# --- Helper Function to Run Scripts ---
def _run_script(script_name: str, args: list[str] = [], use_sudo: bool = False):
    """Finds and runs a script from the 'commands' directory."""
    python_executable = sys.executable
    cli_dir = Path(__file__).parent
    script_path = cli_dir / script_name

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
    path: Optional[str] = typer.Option(
        None, "--path", "-p", help="Path to create project (default: ~/Coding/projects)"
    ),
    type: str = typer.Option(
        "lib", "--type", help="Project type: app, cli, or lib (default: lib)"
    ),
    no_docs: bool = typer.Option(
        False, "--no-docs", help="Do not generate documentation files (README.md, LICENSE, pyproject.toml, .gitignore). Project will not be buildable with uv/hatchling until you add the required files."
    ),
    description: str = typer.Option(
        "Add your description here", "--description", help="Project description for README and pyproject.toml"
    ),
    author: str = typer.Option(
        "Your Name", "--author", help="Author name for LICENSE and pyproject.toml"
    ),
    email: str = typer.Option(
        "your.email@example.com", "--email", help="Author email for pyproject.toml"
    ),
    license_type: str = typer.Option(
        "MIT", "--license-type", help="License type for documentation files (MIT, Apache-2.0, GPL-3.0)"
    ),
    no_venv: bool = typer.Option(
        False, "--no-venv", help="Skip virtual environment creation"
    ),
    no_git: bool = typer.Option(
        False, "--no-git", help="Skip Git repository initialization"
    ),
    open: bool = typer.Option(
        False, "--open", "-o", help="Open in Sublime Text after creation"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", help="Prompt interactively for all project options."
    ),
):
    args = [project_name]
    if path:
        args.extend(["--path", path])
    if type:
        args.extend(["--type", type])
    if no_docs:
        args.append("--no-docs")
    if description:
        args.extend(["--description", description])
    if author:
        args.extend(["--author", author])
    if email:
        args.extend(["--email", email])
    if license_type:
        args.extend(["--license-type", license_type])
    if no_venv:
        args.append("--no-venv")
    if no_git:
        args.append("--no-git")
    if open:
        args.append("--open")
    if interactive:
        args.append("--interactive")

    _run_script("project_generator.py", args)


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


@subtitle_app.command("sync")
def subtitle_sync(
    video_path: Path = typer.Argument(..., help="Path to the reference video file."),
    input_srt: Path = typer.Argument(..., help="Path to the out-of-sync .srt file."),
    output_srt: Path = typer.Argument(..., help="Path for the new, synced .srt file."),
):
    """Automatically syncs subtitles to a video using audio analysis."""
    _run_script(
        "subtitle_manager.py",
        ["sync", str(video_path), str(input_srt), str(output_srt)],
    )


@subtitle_app.command("shift")
def subtitle_shift(
    input_srt: Path = typer.Argument(..., help="Path to the original .srt file."),
    output_srt: Path = typer.Argument(..., help="Path for the new, shifted .srt file."),
    # Changed from string to float to match the new function
    offset: float = typer.Option(
        ..., "--offset", "-o", help="Time offset in seconds (e.g., -13.0)."
    ),
):
    """Creates a new, time-shifted subtitle file using pysrt."""
    _run_script(
        "subtitle_manager.py",
        ["shift", str(input_srt), str(output_srt), "--offset", str(offset)],
    )


@subtitle_app.command("embed")
def subtitle_embed(
    video_path: Path = typer.Argument(..., help="Path to the input video file."),
    subtitle_path: Path = typer.Argument(..., help="Path to the .srt subtitle file."),
    output_path: Path = typer.Argument(..., help="Path for the new output video file."),
    offset: float = typer.Option(
        0.0, "--offset", "-o", help="Offset in seconds for soft subtitles."
    ),
    hard_sub: bool = typer.Option(
        False, "--hard", help="Burn subtitles into the video (slower, permanent)."
    ),
):
    """Embeds subtitles into a video file (softsub by default)."""
    args = [
        "embed",
        str(video_path),
        str(subtitle_path),
        str(output_path),
        "--offset",
        str(offset),
    ]
    if hard_sub:
        args.append("--hard")
    _run_script("subtitle_manager.py", args)


@gist_app.command("list")
def gist_list():
    """Lists existing GitHub Gists."""
    _run_script("gist_manager.py", ["list"])


@app.command()
def generate_docs(
    dir: str = typer.Option(
        ".",
        "--dir",
        help="Output directory for documentation files (default: current directory)",
    ),
    all: bool = typer.Option(
        False,
        "--all",
        help="Generate all documentation files (README.md, LICENSE, pyproject.toml, .gitignore)",
    ),
    readme: bool = typer.Option(False, "--readme", help="Generate README.md"),
    license: bool = typer.Option(False, "--license", help="Generate LICENSE"),
    pyproject: bool = typer.Option(
        False, "--pyproject", help="Generate pyproject.toml"
    ),
    gitignore: bool = typer.Option(False, "--gitignore", help="Generate .gitignore"),
    project_name: str = typer.Option(
        "my_project",
        "--project-name",
        help="Project name for README and pyproject.toml",
    ),
    package_name: Optional[str] = typer.Option(
        None,
        "--package-name",
        help="Package name for pyproject.toml (defaults to project-name)",
    ),
    description: str = typer.Option(
        "A Python project",
        "--description",
        help="Project description for README and pyproject.toml",
    ),
    author: str = typer.Option(
        "Your Name", "--author", help="Author name for LICENSE and pyproject.toml"
    ),
    email: str = typer.Option(
        "your.email@example.com", "--email", help="Author email for pyproject.toml"
    ),
    license_type: str = typer.Option(
        "MIT", "--license-type", help="License type: MIT, Apache-2.0, GPL-3.0"
    ),
):
    """Generates project documentation files (README.md, LICENSE, pyproject.toml, .gitignore)."""
    args = [
        "--dir",
        dir,
        "--project-name",
        project_name,
        "--description",
        description,
        "--author",
        author,
        "--email",
        email,
        "--license-type",
        license_type,
    ]
    if all:
        args.append("--all")
    if readme:
        args.append("--readme")
    if license:
        args.append("--license")
    if pyproject:
        args.append("--pyproject")
    if gitignore:
        args.append("--gitignore")
    if package_name:
        args.extend(["--package-name", package_name])
    _run_script("docs_generator.py", args)


@gist_app.command("upload")
def gist_upload(
    file_paths: List[str] = typer.Argument(
        ..., help="Paths to the files to upload as a gist."
    ),
    description: str = typer.Option(
        "", "--description", "-d", help="Description for the gist."
    ),
    public: bool = typer.Option(
        False, "--public", help="Create a public gist (default: secret)."
    ),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="Skip prompting and create new gist."
    ),
):
    """Uploads files as a new GitHub Gist."""
    args = ["upload"] + list(file_paths)
    if description:
        args.extend(["--description", description])
    if public:
        args.append("--public")
    if non_interactive:
        args.append("--non-interactive")
    _run_script("gist_manager.py", args)


@gist_app.command("update")
def gist_update(
    gist_identifier: str = typer.Argument(
        ..., help="Gist ID or filename to identify the gist to update."
    ),
    file_paths: Optional[List[str]] = typer.Argument(
        None,
        help="Paths to the files to update (optional for description-only updates).",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="New description for the gist (uses existing if not provided).",
    ),
    description_only: bool = typer.Option(
        False,
        "--description-only",
        help="Update only the description, keeping all existing files. Use with --description.",
    ),
):
    """Updates an existing GitHub Gist by filename or ID."""
    # Safety check: if no files provided and no description, show error
    if not file_paths and not description:
        typer.echo(
            "❌ Error: You must provide either files to update or a new description",
            err=True,
        )
        typer.echo("Examples:", err=True)
        typer.echo("  automations gist update abc123 file1.py file2.py", err=True)
        typer.echo(
            "  automations gist update abc123 --description 'New description' --description-only",
            err=True,
        )
        typer.echo(
            "  automations gist update abc123 file1.py --description 'New description'",
            err=True,
        )
        raise typer.Exit(1)

    # Safety check: if description_only is used, ensure no files are provided
    if description_only and file_paths:
        typer.echo("❌ Error: Cannot use --description-only with file paths", err=True)
        raise typer.Exit(1)

    # Safety check: if description_only is used, ensure description is provided
    if description_only and not description:
        typer.echo("❌ Error: --description-only requires --description", err=True)
        raise typer.Exit(1)

    # Safety check: if only description is provided without --description-only flag
    if description and not file_paths and not description_only:
        typer.echo(
            "❌ Error: To update only the description, use --description-only to avoid accidentally deleting files",
            err=True,
        )
        typer.echo(
            "Use: automations gist update {} --description '{}' --description-only".format(
                gist_identifier, description
            ),
            err=True,
        )
        raise typer.Exit(1)

    args = ["update"]
    # Add file paths if provided (this will be empty for description-only updates)
    if file_paths:
        args.extend(list(file_paths))
    args.extend(["--update", gist_identifier])
    if description:
        args.extend(["--description", description])
    _run_script("gist_manager.py", args)


@gist_app.command("delete")
def gist_delete(
    gist_identifier: str = typer.Argument(
        ..., help="Gist ID or filename to identify the gist to delete."
    ),
):
    """Deletes a GitHub Gist by filename or ID."""
    args = ["delete", gist_identifier]
    _run_script("gist_manager.py", args)


@gist_app.command("download")
def gist_download(
    gist_id_or_url: str = typer.Argument(
        ..., help="Gist ID or full gist URL to download."
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", help="Directory to save the gist files (default: ./gist-<id>)."
    ),
):
    """
    Download a GitHub Gist by ID or URL and save its files locally.
    """
    args = ["download", gist_id_or_url]
    if output_dir:
        args.extend(["--output-dir", output_dir])
    _run_script("gist_manager.py", args)


if __name__ == "__main__":
    app()
