#!/usr/bin/env python3
import sys
import subprocess
import configparser
from pathlib import Path
import argparse

TORRENT_CONFIG_FILE = Path.home() / ".torrent_downloader_config.ini"
TORRENT_DEFAULT_CONFIG = {
    "output_dir": str(Path.home() / "Downloads" / "Torrents"),
    "max_connections": "16",  # aria2c max for torrents is 16
    "max_download": "",
    "max_upload": "",
    "seed": "false",
    "session_file": str(Path.home() / ".aria2.session"),
}


def load_torrent_config():
    config = configparser.ConfigParser()
    if TORRENT_CONFIG_FILE.exists():
        config.read(TORRENT_CONFIG_FILE)
        if "settings" in config:
            return dict(config["settings"])
    return TORRENT_DEFAULT_CONFIG.copy()


def save_torrent_config(config_dict):
    config = configparser.ConfigParser()
    config["settings"] = config_dict
    with open(TORRENT_CONFIG_FILE, "w") as f:
        config.write(f)


def ensure_session_file(session_file):
    session_path = Path(session_file)
    if not session_path.exists():
        session_path.touch()


def main():
    parser = argparse.ArgumentParser(
        description="Download torrents using aria2c with pause/resume, speed limits, and config support."
    )
    parser.add_argument(
        "torrents", nargs="*", help="One or more .torrent files or magnet links."
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
        "--pause",
        action="store_true",
        help="Pause all downloads (not implemented, placeholder).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume all downloads (not implemented, placeholder).",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress aria2c output except errors."
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default configuration file and exit.",
    )

    args = parser.parse_args()

    if args.create_config:
        save_torrent_config(TORRENT_DEFAULT_CONFIG)
        print(f"✅ Default torrent config created at {TORRENT_CONFIG_FILE}")
        sys.exit(0)

    if not args.torrents:
        print(
            "❌ Error: You must provide at least one .torrent file or magnet link.",
            file=sys.stderr,
        )
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
        print(
            "❌ Error: --max-connections must be between 1 and 16 for torrents.",
            file=sys.stderr,
        )
        sys.exit(1)

    aria2_args = [
        "aria2c",
        "--dir",
        output_dir,
        "--max-connection-per-server",
        str(max_connections),
        "--seed-time=0" if not seed else "--seed-time=60",
        "--continue=true",
    ]

    # Only use session file if --session, --pause, or --resume is specified
    use_session = args.session or args.pause or args.resume
    if use_session:
        ensure_session_file(session_file)
        aria2_args.extend(
            [
                "--save-session",
                session_file,
                "--input-file",
                session_file,
            ]
        )

    if max_download:
        aria2_args.extend(["--max-download-limit", max_download])
    if max_upload:
        aria2_args.extend(["--max-upload-limit", max_upload])
    if args.quiet:
        aria2_args.extend(
            ["--quiet=true", "--console-log-level=warn", "--summary-interval=0"]
        )
    else:
        aria2_args.append("--summary-interval=5")

    aria2_args.extend(args.torrents)

    print(f"▶️  Running: {' '.join(aria2_args)}")
    try:
        subprocess.run(aria2_args, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ aria2c exited with error code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
