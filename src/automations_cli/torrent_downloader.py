#!/usr/bin/env python3
import re
import sys
import time
import signal
import select
import argparse
import subprocess
import configparser
from pathlib import Path

try:
    from helper.configs import setup_logging, CONFIG_DIR
except ImportError:
    from .helper.configs import setup_logging

logger = setup_logging(log_file="torrent_downloader.log")

TORRENT_CONFIG_FILE = CONFIG_DIR / ".torrent_downloader_config.ini"
TORRENT_DEFAULT_CONFIG = {
    "output_dir": str(Path.home() / "Downloads" / "Torrents"),
    "max_connections": "16",
    "max_download": "",
    "max_upload": "",
    "seed": "false",
    "session_file": str(CONFIG_DIR / ".aria2.session"),
}


def load_torrent_config():
    """Loads torrent configuration from the config file."""
    config = configparser.ConfigParser()
    if TORRENT_CONFIG_FILE.exists():
        logger.debug(f"Loading config from {TORRENT_CONFIG_FILE}")
        config.read(TORRENT_CONFIG_FILE)
        if "settings" in config:
            loaded_config = dict(config["settings"])
            logger.debug(f"Loaded config: {loaded_config}")
            return loaded_config
    logger.debug("Using default config")
    return TORRENT_DEFAULT_CONFIG.copy()


def save_torrent_config(config_dict):
    """Saves the torrent configuration to the config file."""
    config = configparser.ConfigParser()
    config["settings"] = config_dict
    try:
        with open(TORRENT_CONFIG_FILE, "w") as f:
            config.write(f)
        logger.info(f"Config saved to {TORRENT_CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise


def ensure_session_file(session_file):
    """Ensures that the session file exists."""
    session_path = Path(session_file)
    if not session_path.exists():
        try:
            session_path.touch()
            logger.debug(f"Created session file: {session_file}")
        except Exception as e:
            logger.error(f"Failed to create session file {session_file}: {e}")
            raise
    else:
        logger.debug(f"Session file exists: {session_file}")


def validate_torrents(torrents):
    """Validates a list of torrents (magnet links or file paths)."""
    valid_torrents = []
    for torrent in torrents:
        if torrent.startswith("magnet:"):
            logger.debug(f"Valid magnet link: {torrent[:50]}...")
            valid_torrents.append(torrent)
        else:
            torrent_path = Path(torrent)
            if torrent_path.exists() and torrent_path.suffix.lower() == ".torrent":
                logger.debug(f"Valid torrent file: {torrent}")
                valid_torrents.append(str(torrent_path.resolve()))
            else:
                logger.warning(f"Invalid torrent file or magnet link: {torrent}")
    return valid_torrents


def format_size(size_str):
    """Formats a size string to be more readable."""
    if not size_str or size_str == "0B":
        return "0B"
    size_str = size_str.replace("i", "")
    return size_str


def format_time(time_str):
    """Formats a time string to be more readable."""
    if not time_str or time_str == "0s":
        return "0s"
    if "h" in time_str and "m" in time_str:
        return time_str.replace("h", "h ").replace("m", "m")
    return time_str


def clear_line():
    """Clears the current line in the console."""
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def print_progress(message, width=80):
    """Prints a progress message to the console."""
    clear_line()
    if len(message) > width - 4:
        message = message[: width - 7] + "..."
    sys.stdout.write(f"\r{message}")
    sys.stdout.flush()


def parse_torrent_name(magnet_or_file):
    """Parses the name of a torrent from a magnet link or file path."""
    if magnet_or_file.startswith("magnet:"):
        match = re.search(r"dn=([^&]+)", magnet_or_file)
        if match:
            import urllib.parse

            return urllib.parse.unquote(match.group(1))
        return "Unknown Torrent"
    return Path(magnet_or_file).stem


def parse_aria2c_progress(line, verbose=False):
    """Parses the progress line from aria2c's output."""
    if verbose:
        logger.info(f"Raw line: {line}")

    seeding_pattern = r"\[#[a-f0-9]{6}\s+SEED\((.+?)\)\s+CN:(\d+)\s+SD:(\d+)\s+UL:([^\s]+)\(([^)]+)\)\]"
    base_pattern = r"\[#[a-f0-9]{6}\s+(.+?)\s+CN:(\d+)\s+SD:(\d+)(?:\s+DL:([^\s]+))?(?:\s+UL:([^\s]+))?(?:\s+ETA:([^\]]+))?\]"

    match = re.match(seeding_pattern, line)
    if match:
        if verbose:
            logger.info(f"Seeding pattern matched: {match.groups()}")
        progress_part, connections, seeders, ul_speed, ul_total = match.groups()
        return {
            "progress": f"SEED({progress_part})",
            "connections": connections,
            "seeders": seeders,
            "dl_speed": "0B",
            "ul_speed": ul_speed,
            "eta": None,
            "ul_total": ul_total,
            "is_metadata": False,
            "is_complete": True,
        }

    match = re.match(base_pattern, line)
    if not match:
        if verbose:
            logger.info("No match found")
        return None

    progress_part, connections, seeders, dl_speed, ul_speed, eta = match.groups()
    dl_speed = dl_speed or "0B"
    ul_speed = ul_speed or "0B"

    if verbose:
        logger.info(f"Progress: {progress_part}")
        logger.info(f"Connections: {connections}")
        logger.info(f"Seeders: {seeders}")
        logger.info(f"DL Speed: {dl_speed}")
        logger.info(f"UL Speed: {ul_speed}")
        logger.info(f"ETA: {eta}")

    is_complete = "100%" in progress_part

    return {
        "progress": progress_part,
        "connections": connections,
        "seeders": seeders,
        "dl_speed": dl_speed,
        "ul_speed": ul_speed,
        "eta": eta,
        "ul_total": None,
        "is_metadata": False,
        "is_complete": is_complete,
    }


def main():
    """Main function to run the torrent downloader."""
    parser = argparse.ArgumentParser(
        description="Download torrents using aria2c with pause/resume, speed limits, and config support."
    )

    # Define the positional argument for torrents separately.
    parser.add_argument(
        "torrents", nargs="*", help="One or more .torrent files or magnet links."
    )

    # Keep the mutually exclusive group for actions only.
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--pause", action="store_true", help="Pause all downloads in the session."
    )
    action_group.add_argument(
        "--resume", action="store_true", help="Resume all downloads in the session."
    )

    parser.add_argument(
        "--output-dir", "-o", help="Directory to save the downloaded files."
    )
    parser.add_argument(
        "--seed", action="store_true", help="Continue seeding after download completes."
    )
    parser.add_argument(
        "--max-connections",
        "-c",
        type=int,
        help="Maximum number of connections per server (1-16).",
    )
    parser.add_argument(
        "--max-download", "-d", help="Maximum download speed (e.g., 1M, 500K)."
    )
    parser.add_argument(
        "--max-upload", "-u", help="Maximum upload speed (e.g., 500K, 0 for unlimited)."
    )
    parser.add_argument(
        "--session", help="Path to aria2c session file for pause/resume."
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress detailed progress output."
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default configuration file and exit.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output."
    )

    args = parser.parse_args()

    # Manually check for invalid argument combinations.
    if args.torrents and (args.pause or args.resume):
        parser.error("argument `torrents` not allowed with `--pause` or `--resume`")

    if args.create_config:
        try:
            save_torrent_config(TORRENT_DEFAULT_CONFIG)
            print(f"✅ Default config created at {TORRENT_CONFIG_FILE}")
            logger.info("Default config created successfully")
        except Exception as e:
            print(f"❌ Failed to create config: {e}", file=sys.stderr)
            logger.error(f"Failed to create config: {e}")
            sys.exit(1)
        sys.exit(0)

    # Check if any action was specified
    if not any([args.torrents, args.pause, args.resume]):
        error_msg = "You must provide at least one .torrent file/magnet link, or use --pause/--resume."
        print(f"❌ Error: {error_msg}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    config = load_torrent_config()
    output_dir = args.output_dir or config.get(
        "output_dir", TORRENT_DEFAULT_CONFIG["output_dir"]
    )
    max_connections = args.max_connections or int(config.get("max_connections", 16))
    max_download = args.max_download or config.get("max_download", "")
    max_upload = args.max_upload or config.get("max_upload", "")
    session_file = args.session or config.get(
        "session_file", TORRENT_DEFAULT_CONFIG["session_file"]
    )
    seed = args.seed or (config.get("seed", "false").lower() == "true")

    if not (1 <= int(max_connections) <= 16):
        error_msg = "--max-connections must be between 1 and 16 for torrents."
        print(f"❌ Error: {error_msg}", file=sys.stderr)
        logger.error(error_msg)
        sys.exit(1)

    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Output directory: {output_dir}")
    except Exception as e:
        error_msg = f"Failed to create output directory {output_dir}: {e}"
        print(f"❌ Error: {error_msg}", file=sys.stderr)
        logger.error(error_msg)
        sys.exit(1)

    aria2_args = [
        "aria2c",
        "--dir",
        output_dir,
        "--max-connection-per-server",
        str(max_connections),
        "--seed-time=0" if not seed else "--seed-time=60",
        "--continue=true",
        "--follow-torrent=mem",
        "--bt-max-peers=50",
        "--bt-request-peer-speed-limit=100K",
    ]

    use_session = args.session or args.pause or args.resume
    if use_session:
        try:
            ensure_session_file(session_file)
            aria2_args.extend(
                ["--save-session", session_file, "--input-file", session_file]
            )
            logger.debug(f"Using session file: {session_file}")
        except Exception as e:
            error_msg = f"Failed to setup session file: {e}"
            print(f"❌ Error: {error_msg}", file=sys.stderr)
            logger.error(error_msg)
            sys.exit(1)

    if args.pause:
        aria2_args.append("--pause=true")
    if args.resume:
        aria2_args.append("--pause=false")

    if max_download:
        aria2_args.extend(["--max-download-limit", max_download])
    if max_upload:
        aria2_args.extend(["--max-upload-limit", max_upload])

    aria2_args.extend(
        [
            "--summary-interval=1",
            "--download-result=hide",
            "--console-log-level=warn",
        ]
    )

    valid_torrents = []
    if args.torrents:
        valid_torrents = validate_torrents(args.torrents)
        if not valid_torrents:
            error_msg = "No valid torrent files or magnet links found."
            print(f"❌ Error: {error_msg}", file=sys.stderr)
            logger.error(error_msg)
            sys.exit(1)
        if len(valid_torrents) != len(args.torrents):
            skipped_count = len(args.torrents) - len(valid_torrents)
            print(f"⚠️ Skipped {skipped_count} invalid torrent(s)")

        aria2_args.extend(valid_torrents)

    logger.info(f"Starting torrent download with {len(valid_torrents)} torrent(s)")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Max connections: {max_connections}")
    logger.info(f"Seeding: {'enabled' if seed else 'disabled'}")
    if max_download:
        logger.info(f"Download limit: {max_download}")
    if max_upload:
        logger.info(f"Upload limit: {max_upload}")

    logger.debug(f"Full aria2c command: {' '.join(aria2_args)}")

    if not args.quiet:
        print("🚀 Torrent Download Started")
        print("=" * 50)
        if valid_torrents:
            for i, name in enumerate(
                [parse_torrent_name(t) for t in valid_torrents], 1
            ):
                print(f"📄 [{i}] {name}")
        print(f"📁 Output: {output_dir}")
        if max_download or max_upload:
            speed_info = []
            if max_download:
                speed_info.append(f"⬇️ {max_download}")
            if max_upload:
                speed_info.append(f"⬆️ {max_upload}")
            print(f"🚀 Speed limits: {' '.join(speed_info)}")
        if seed:
            print("🌱 Seeding: enabled")
        print("=" * 50)

    if args.verbose:
        print(f"🔧 Command: {' '.join(aria2_args)}")
        print()

    download_completed = False

    def signal_handler(signum, frame):
        logger.info("Received interrupt signal, shutting down...")
        if not args.quiet:
            print_progress("🛑 Stopping download...")
            if download_completed:
                print("\r✅ Download completed successfully!")
                if seed:
                    print("🌱 Seeding was interrupted.")
        try:
            if "process" in locals() and process.poll() is None:
                process.terminate()
        except:
            pass
        sys.exit(130)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        process = subprocess.Popen(
            aria2_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        last_update_time = time.time()
        status_message = "🔄 Initializing download..."
        metadata_completed = False
        in_metadata_phase = True
        metadata_torrent_id = None

        if not args.quiet:
            print_progress(status_message)

        stderr_lines = []

        while True:
            # Use select for non-blocking reads
            ready_to_read, _, _ = select.select([process.stdout], [], [], 0.1)

            if not ready_to_read:
                if process.poll() is not None:
                    break
                continue

            for stream in ready_to_read:
                line = stream.readline().strip()
                if not line:
                    continue

                if "FILE: " in line and "[METADATA]" in line and not metadata_completed:
                    in_metadata_phase = True
                    metadata_torrent_id = line.split()[0].strip("[]")
                    status_message = "🔍 Fetching metadata..."
                    if not args.quiet:
                        print_progress(status_message)
                    continue

                if (
                    in_metadata_phase
                    and not metadata_torrent_id
                    and re.match(r"\[#[a-f0-9]{6}\s", line)
                ):
                    metadata_torrent_id = line.split()[0].strip("[]")
                    status_message = "🔍 Fetching metadata..."
                    if not args.quiet:
                        print_progress(status_message)
                    logger.debug(f"Set metadata_torrent_id to {metadata_torrent_id}")

                progress_data = parse_aria2c_progress(line, args.verbose)

                if progress_data and not args.quiet:
                    current_time = time.time()
                    if current_time - last_update_time < 0.5:
                        continue

                    last_update_time = current_time

                    progress_part = progress_data["progress"]
                    dl_speed = (
                        format_size(progress_data["dl_speed"].strip())
                        if progress_data["dl_speed"]
                        else "0B"
                    )
                    ul_speed = (
                        format_size(progress_data["ul_speed"].strip())
                        if progress_data["ul_speed"]
                        else "0B"
                    )
                    eta = (
                        format_time(progress_data["eta"].strip())
                        if progress_data["eta"]
                        else None
                    )
                    torrent_id = line.split()[0].strip("[]")

                    progress_data["is_metadata"] = (
                        in_metadata_phase and torrent_id == metadata_torrent_id
                    )

                    if progress_data["is_metadata"] and progress_part == "0B/0B":
                        status_message = "🔍 Metadata: waiting for peers..."
                        print_progress(status_message)
                        continue

                    if (
                        progress_data["is_metadata"]
                        and progress_data["is_complete"]
                        and not metadata_completed
                    ):
                        logger.info("Torrent metadata download completed")
                        metadata_completed = True
                        in_metadata_phase = False
                        metadata_torrent_id = None
                        status_message = "🔄 Fetching torrent files..."
                        print_progress(status_message)
                        time.sleep(1)
                        continue

                    if "SEED" in progress_part and not download_completed:
                        logger.info("Download completed successfully")
                        print("\r✅ Download completed successfully!")
                        if seed:
                            print("🌱 Seeding will continue in the background...")
                        download_completed = True

                    if progress_data["is_metadata"]:
                        status_parts = [f"🔍 Metadata: {progress_part}"]
                    else:
                        status_parts = [f"📥 {progress_part}"]

                    if dl_speed and dl_speed != "0B":
                        status_parts.append(f"⬇️ {dl_speed}/s")

                    status_parts.append(f"⬆️ {ul_speed}/s")

                    if eta and eta != "0s":
                        status_parts.append(f"⏱️ {eta}")

                    if progress_data.get("ul_total"):
                        status_parts.append(
                            f"📤 Total Uploaded: {format_size(progress_data['ul_total'])}"
                        )

                    status_message = " | ".join(status_parts)
                    print_progress(status_message)

                elif "ERROR" in line or "WARN" in line:
                    stderr_lines.append(line)
                    if not args.quiet:
                        clear_line()
                        print(f"⚠️ {line}")
                        print_progress(status_message)

        process.wait()

        stderr_output = process.stderr.read()
        if stderr_output:
            stderr_lines.append(stderr_output)

        if not args.quiet:
            clear_line()

        if process.returncode == 0:
            if not download_completed and not metadata_completed:
                logger.info("Download completed successfully")
                print("✅ Download completed successfully!")
                if seed:
                    print("🌱 Seeding will continue in the background...")
        else:
            error_output = "\n".join(stderr_lines).strip()
            error_msg = f"Download failed (exit code: {process.returncode})"
            if not args.quiet:
                print(f"❌ {error_msg}")
            if error_output:
                logger.error(f"{error_msg}\n{error_output}")
                if not args.quiet:
                    print(f"📋 Error details: {error_output}")
            else:
                logger.error(error_msg)
            sys.exit(process.returncode)

    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        if not args.quiet:
            clear_line()
            print("⏹️ Download interrupted by user")
        sys.exit(130)
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        if not args.quiet:
            clear_line()
            print(f"❌ {error_msg}")
        logger.error(error_msg, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
