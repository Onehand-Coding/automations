#!/usr/bin/env python3
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    from helper.configs import setup_logging
except ImportError:
    from .helper.configs import setup_logging

logger = setup_logging(log_file="file_downloader.log")

DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"


def is_valid_url(url: str) -> bool:
    """Validate if the URL is properly formatted."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def detect_download_method(url: str) -> str:
    """Automatically detect the best download method based on URL and available tools."""
    # Check available tools
    has_wget = shutil.which("wget") is not None
    has_curl = shutil.which("curl") is not None

    if not has_wget and not has_curl:
        raise RuntimeError(
            "Neither wget nor curl is available. Please install one of them."
        )

    # Prefer wget for most cases as it handles resuming better
    if has_wget:
        return "wget"
    else:
        return "curl"


def download_with_wget(
    url: str, output_path: Path, resume: bool = True, quiet: bool = False
) -> bool:
    """Download file using wget."""
    command = ["wget"]

    if resume:
        command.append("--continue")

    if quiet:
        command.append("--quiet")
    else:
        command.append("--progress=bar:force")

    command.extend(["-O", str(output_path), url])

    logger.info(f"Executing wget command: {' '.join(command)}")
    print(f"📥 Downloading with wget: {url}")

    try:
        result = subprocess.run(command, check=True, capture_output=not quiet)
        logger.info("Download completed successfully")
        print(f"✅ Download complete: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"wget failed with return code {e.returncode}")
        print(f"❌ Download failed: {e}", file=sys.stderr)
        return False


def download_with_curl(
    url: str, output_path: Path, resume: bool = True, quiet: bool = False
) -> bool:
    """Download file using curl."""
    command = ["curl"]

    if resume:
        command.append("--continue-at")
        command.append("-")

    if quiet:
        command.append("--silent")
    else:
        command.append("--progress-bar")

    command.extend(["-L", "-o", str(output_path), url])

    logger.info(f"Executing curl command: {' '.join(command)}")
    print(f"📥 Downloading with curl: {url}")

    try:
        result = subprocess.run(command, check=True, capture_output=not quiet)
        logger.info("Download completed successfully")
        print(f"✅ Download complete: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"curl failed with return code {e.returncode}")
        print(f"❌ Download failed: {e}", file=sys.stderr)
        return False


def download_file(
    url: str,
    output_name: Optional[str] = None,
    output_dir: Optional[str] = None,
    method: str = "auto",
    resume: bool = True,
    quiet: bool = False,
):
    """Download a file from a URL."""
    if not is_valid_url(url):
        error_msg = f"Invalid URL format: {url}"
        logger.error(error_msg)
        print(f"❌ {error_msg}", file=sys.stderr)
        return

    # Determine download method
    if method == "auto":
        method = detect_download_method(url)

    # Determine output path
    if output_dir:
        output_dir_path = Path(output_dir)
    else:
        output_dir_path = DEFAULT_DOWNLOAD_DIR

    output_dir_path.mkdir(parents=True, exist_ok=True)

    if output_name:
        output_path = output_dir_path / output_name
    else:
        # Extract filename from URL
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        if not filename or filename == "/":
            filename = "downloaded_file"
        output_path = output_dir_path / filename

    logger.info(f"Downloading {url} to {output_path}")

    # Perform download
    if method == "wget":
        success = download_with_wget(url, output_path, resume, quiet)
    elif method == "curl":
        success = download_with_curl(url, output_path, resume, quiet)
    else:
        error_msg = f"Unknown download method: {method}"
        logger.error(error_msg)
        print(f"❌ {error_msg}", file=sys.stderr)
        return

    if success:
        # Show file info
        if output_path.exists():
            size = output_path.stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"📁 File saved: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download files from URLs using wget or curl."
    )
    parser.add_argument("url", help="The URL of the file to download.")
    parser.add_argument("--output-name", help="Optional output filename.")
    parser.add_argument(
        "--output-dir", "-o", help="Directory to save the file (default: ~/Downloads)."
    )
    parser.add_argument(
        "--method",
        "-m",
        choices=["auto", "wget", "curl"],
        default="auto",
        help="Download method: auto, wget, curl (default: auto).",
    )
    parser.add_argument(
        "--no-resume", action="store_true", help="Disable resume functionality."
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress output (quiet mode)."
    )

    args = parser.parse_args()

    download_file(
        url=args.url,
        output_name=args.output_name,
        output_dir=args.output_dir,
        method=args.method,
        resume=not args.no_resume,
        quiet=args.quiet,
    )
