import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import re
import configparser
from urllib.parse import urlparse

try:
    from helper.configs import setup_logging
except ImportError:
    from .helper.configs import setup_logging

logger = setup_logging(log_file="video_downloader.log")

YT_DLP_DEFAULT_DIR = Path.home() / "Downloads" / "Yt-dlp"
CONFIG_FILE = Path.home() / ".video_downloader_config.ini"
DEFAULT_CONFIG = {
    "default_quality": "best",
    "default_output_dir": str(YT_DLP_DEFAULT_DIR),
    "continue_downloads": "true",
    "no_overwrites": "true",
    "progress": "true",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Brave/1.66.118",
}


def load_config() -> Dict[str, Any]:
    """Load configuration from config file."""
    config = configparser.ConfigParser()

    if CONFIG_FILE.exists():
        try:
            config.read(CONFIG_FILE)
            if "settings" in config:
                return dict(config["settings"])
        except Exception as e:
            logger.warning(f"Could not read config file: {e}")

    return DEFAULT_CONFIG


def save_config(config_dict: Dict[str, Any]):
    """Save configuration to config file."""
    config = configparser.ConfigParser()
    config["settings"] = config_dict

    try:
        with open(CONFIG_FILE, "w") as f:
            config.write(f)
        logger.info(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Could not save config file: {e}")


def is_valid_url(url: str) -> bool:
    """Validate if the URL is properly formatted."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def list_formats(url: str) -> bool:
    """List available formats for the given URL."""
    if not shutil.which("yt-dlp"):
        error_msg = "'yt-dlp' command not found."
        logger.error(error_msg)
        print(f"❌ {error_msg}", file=sys.stderr)
        return False

    if not is_valid_url(url):
        error_msg = f"Invalid URL format: {url}"
        logger.error(error_msg)
        print(f"❌ {error_msg}", file=sys.stderr)
        return False

    logger.info(f"Listing formats for URL: {url}")
    print(f"📋 Available formats for: {url}")

    command = ["yt-dlp", "--list-formats", url]

    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Failed to list formats. yt-dlp exited with error code {e.returncode}."
        )
        logger.error(error_msg)
        print(f"❌ {error_msg}", file=sys.stderr)
        return False
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        logger.exception(error_msg)
        print(f"❌ {error_msg}", file=sys.stderr)
        return False


def parse_progress(line: str) -> Optional[Dict[str, str]]:
    """Parse yt-dlp progress output."""
    # Match download progress pattern
    progress_pattern = (
        r"\[download\]\s+(\d+\.?\d*)%\s+of\s+~?\s*([0-9.]+\w+)\s+at\s+([0-9.]+\w+/s)"
    )
    match = re.search(progress_pattern, line)

    if match:
        return {
            "percent": match.group(1),
            "size": match.group(2),
            "speed": match.group(3),
        }
    return None


def handle_playlist_options(
    command: list,
    playlist_mode: str = "download_all",
    playlist_items: Optional[str] = None,
):
    """Add playlist-specific options to command."""
    if playlist_items:
        command.extend(["--playlist-items", playlist_items])
        logger.info(f"Targeting specific playlist items: {playlist_items}")

    if playlist_mode == "download_all":
        pass
    elif playlist_mode == "single":
        command.append("--no-playlist")
    elif playlist_mode == "first_n" and not playlist_items:
        command.extend(["--playlist-end", "5"])
    elif playlist_mode == "audio_only":
        logger.info("Setting download mode to audio only.")
        command.extend(
            ["-f", "bestaudio/best", "--extract-audio", "--audio-format", "mp3"]
        )


def download(
    url: str,
    output_name: Optional[str] = None,
    quality: str = "best",
    playlist_mode: str = "download_all",
    use_config: bool = True,
    playlist_items: Optional[str] = None,
    browser: Optional[str] = None,
    archive: Optional[str] = None,
):
    """
    Downloads a video from a URL using yt-dlp. Always saves to a predictable location.

    Args:
        url: The URL of the video to download
        output_name: Optional output filename
        quality: Desired video quality
        playlist_mode: How to handle playlists ('download_all', 'single', 'first_n', 'audio_only')
        use_config: Whether to use config file settings
    """
    if not shutil.which("yt-dlp"):
        error_msg = "'yt-dlp' command not found."
        logger.error(error_msg)
        print(f"❌ {error_msg}", file=sys.stderr)
        return

    # Validate URL
    if not is_valid_url(url):
        error_msg = f"Invalid URL format: {url}"
        logger.error(error_msg)
        print(f"❌ {error_msg}", file=sys.stderr)
        return

    # Load config
    config = load_config() if use_config else {}

    # Use config values as defaults
    quality = quality if quality != "best" else config.get("default_quality", "best")
    output_dir = Path(config.get("default_output_dir", str(YT_DLP_DEFAULT_DIR)))

    logger.info(f"Starting download for URL: {url}")
    logger.info(f"Quality target: {quality}")
    logger.info(f"Playlist mode: {playlist_mode}")

    command = ["yt-dlp"]

    command.append("--embed-thumbnail")

    if archive:
        command.extend(["--download-archive", archive])

    if browser:
        command.extend(["--cookies-from-browser", browser])
        logger.info(f"Using cookies from browser: {browser}")

    user_agent = config.get("user_agent")
    if user_agent:
        command.extend(["--user-agent", user_agent])

    # Add options based on config
    if config.get("continue_downloads", "true").lower() == "true":
        command.append("--continue")
    if config.get("no_overwrites", "true").lower() == "true":
        command.append("--no-overwrites")
    if config.get("progress", "true").lower() == "true":
        command.append("--progress")

    # --- OUTPUT LOGIC ---
    if output_name:
        if Path(output_name).is_absolute():
            final_output_path = Path(output_name)
        else:
            final_output_path = output_dir / output_name
    else:
        final_output_path = output_dir / "%(title)s.%(ext)s"

    final_output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_name and not Path(output_name).suffix:
        final_output_path = final_output_path.with_suffix(".mp4")

    logger.info(f"Final output path determined: {final_output_path}")
    command.extend(["-o", str(final_output_path)])
    print(f"▶️  Saving to: '{final_output_path.parent}'")

    # --- Handle playlist options ---
    handle_playlist_options(command, playlist_mode, playlist_items)

    # --- Format Selection Logic ---
    # --- Only set video quality if NOT in audio_only mode ---
    if playlist_mode != "audio_only":
        if quality == "best":
            command.extend(["-S", "res,vbr,abr"])
        else:
            clean_quality = quality.removesuffix("p")
            format_string = f"bestvideo[height<=?{clean_quality}]+bestaudio/best[height<=?{clean_quality}]/best"
            command.extend(["-f", format_string])

    command.append(url)

    logger.debug(f"Executing command: {' '.join(command)}")

    try:
        # Use Popen for real-time progress tracking
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        # Track progress
        last_progress = None
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if line:
                # Parse and display progress
                progress = parse_progress(line)
                if progress and progress != last_progress:
                    print(
                        f"\r📥 Progress: {progress['percent']}% ({progress['size']}) at {progress['speed']}",
                        end="",
                        flush=True,
                    )
                    last_progress = progress
                elif "[download]" in line and "Destination:" in line:
                    print(f"\n📁 {line}")
                elif "[download]" in line and "has already been downloaded" in line:
                    print(f"\n✅ {line}")
                elif "ERROR" in line.upper():
                    print(f"\n❌ {line}")
                    logger.error(line)

        # Wait for process to complete
        return_code = process.wait()

        if return_code == 0:
            logger.info("✅ Download process completed successfully.")
            print("\n✅ Download complete!")
        else:
            error_msg = f"Download failed. yt-dlp exited with error code {return_code}."
            logger.error(error_msg)
            print(f"\n❌ {error_msg}", file=sys.stderr)

    except KeyboardInterrupt:
        interrupted_msg = (
            "\n\n⏹️ Download interrupted by user. Run the same command again to resume."
        )
        logger.warning("Download interrupted by user.")
        print(interrupted_msg)
        sys.exit(0)

    except Exception as e:
        unexpected_error = f"An unexpected error occurred: {e}"
        logger.exception(unexpected_error)
        print(f"\n❌ {unexpected_error}", file=sys.stderr)


def create_default_config():
    """Create a default configuration file."""
    save_config(DEFAULT_CONFIG)
    print(f"✅ Default configuration created at {CONFIG_FILE}")
    print("You can edit this file to customize default settings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enhanced yt-dlp video downloader wrapper."
    )
    parser.add_argument("url", nargs="?", help="The URL of the video to download.")
    parser.add_argument(
        "output_name", nargs="?", default=None, help="Optional output filename."
    )
    parser.add_argument(
        "--quality",
        default="best",
        help="Desired video quality (e.g., 720p, 1080p, best).",
    )
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="List available formats for the URL.",
    )
    parser.add_argument(
        "--playlist-mode",
        default="download_all",
        choices=["download_all", "single", "first_n", "audio_only"],
        help="How to handle playlists.",
    )
    parser.add_argument(
        "--items",
        type=str,
        default=None,
        help="Download specific items from a playlist.",
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default configuration file.",
    )
    parser.add_argument(
        "--no-config", action="store_true", help="Don't use configuration file."
    )
    parser.add_argument(
        "--browser",
        type=str,
        default=None,
        help="Browser to use for cookies (e.g., 'brave').",
    )
    parser.add_argument(
        "--archive", type=str, default=None, help="Path to download archive file."
    )

    args = parser.parse_args()

    # Handle special commands
    if args.create_config:
        create_default_config()
        sys.exit(0)

    if args.list_formats:
        if not args.url:
            print("❌ URL is required when using --list-formats", file=sys.stderr)
            sys.exit(1)
        success = list_formats(args.url)
        sys.exit(0 if success else 1)

    # Validate that URL is provided for download
    if not args.url:
        print("❌ URL is required for download", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Perform download
    download(
        url=args.url,
        output_name=args.output_name,
        quality=args.quality,
        playlist_mode=args.playlist_mode,
        playlist_items=args.items,
        use_config=not args.no_config,
        browser=args.browser,
        archive=args.archive,
    )
