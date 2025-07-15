#!/usr/bin/env python3
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List
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


def detect_download_method() -> str:
    """Automatically detect the best download method based on available tools."""
    has_aria2 = shutil.which("aria2c") is not None
    has_wget = shutil.which("wget") is not None
    has_curl = shutil.which("curl") is not None

    if has_aria2:
        return "aria2"
    elif has_wget:
        return "wget"
    elif has_curl:
        return "curl"
    else:
        raise RuntimeError(
            "None of aria2c, wget, or curl is available. Please install one of them."
        )


def parse_aria2c_progress(line):
    """Parse aria2c progress line for single file downloads."""
    import re

    # Example: [#1f3b2c 4.2MiB/10MiB(42%) CN:5 DL:1.2MiB ETA:5s]
    pattern = r"\[#\w+\s+([0-9.]+[KMG]?i?B)/([0-9.]+[KMG]?i?B)\((\d+)%\)\s+CN:(\d+)\s+DL:([0-9.]+[KMG]?i?B)\s+ETA:([0-9a-zA-Z]+)\]"
    match = re.match(pattern, line)
    if match:
        downloaded, total, percent, connections, speed, eta = match.groups()
        return {
            "downloaded": downloaded,
            "total": total,
            "percent": percent,
            "connections": connections,
            "speed": speed,
            "eta": eta,
        }
    return None


def download_with_aria2(
    urls: List[str],
    output_dir: Path,
    output_name: Optional[str] = None,
    resume: bool = True,
    quiet: bool = False,
) -> bool:
    """Download one or more files using aria2c with progress parsing."""
    command = [
        "aria2c",
        "--dir",
        str(output_dir),
        "--max-connection-per-server=8",
        "--summary-interval=1",
        "--console-log-level=warn",
        "--allow-overwrite=true",
    ]
    if resume:
        command.append("--continue=true")
    else:
        command.append("--continue=false")

    # If only one file and output_name is given, use --out
    if output_name and len(urls) == 1:
        command.extend(["--out", output_name])

    command.extend(urls)

    logger.info(f"Executing aria2c command: {' '.join(command)}")
    print(f"📥 Downloading with aria2c: {', '.join(urls)}")

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
        last_progress = None
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            progress = parse_aria2c_progress(line)
            if progress and not quiet:
                print(
                    f"\r📥 {progress['percent']}% of {progress['total']} at {progress['speed']} ETA {progress['eta']}",
                    end="",
                    flush=True,
                )
                last_progress = progress
        process.wait()
        if not quiet:
            print()  # Newline after progress
        if process.returncode == 0:
            logger.info("Download completed successfully")
            print(f"✅ Download complete in {output_dir}")
            return True
        else:
            logger.error(f"aria2c failed with return code {process.returncode}")
            print(
                f"❌ Download failed: aria2c exited with {process.returncode}",
                file=sys.stderr,
            )
            return False
    except Exception as e:
        logger.error(f"aria2c failed: {e}")
        print(f"❌ Download failed: {e}", file=sys.stderr)
        return False


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


def download_files(
    urls: List[str],
    output_name: Optional[str] = None,
    output_dir: Optional[str] = None,
    method: str = "auto",
    resume: bool = True,
    quiet: bool = False,
):
    """Download multiple files from URLs using aria2c, wget, or curl with fallback."""
    if not urls:
        print("❌ No URLs provided.", file=sys.stderr)
        return

    # Validate URLs
    for url in urls:
        if not is_valid_url(url):
            error_msg = f"Invalid URL format: {url}"
            logger.error(error_msg)
            print(f"❌ {error_msg}", file=sys.stderr)
            return

    # Determine output path
    output_dir_path = Path(output_dir) if output_dir else DEFAULT_DOWNLOAD_DIR
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Try aria2c for all files if selected or auto
    if method == "aria2" or (method == "auto" and shutil.which("aria2c")):
        success = download_with_aria2(urls, output_dir_path, output_name, resume, quiet)
        if success:
            for url in urls:
                filename = (
                    output_name
                    if output_name and len(urls) == 1
                    else Path(urlparse(url).path).name or "downloaded_file"
                )
                file_path = output_dir_path / filename
                if file_path.exists():
                    size = file_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    print(f"📁 File saved: {file_path} ({size_mb:.1f} MB)")
            return

    # Otherwise, loop over URLs and use wget/curl with fallback
    for i, url in enumerate(urls):
        name = output_name if output_name and len(urls) == 1 else None
        # Try each method in order
        for m in [method] if method != "auto" else ["wget", "curl"]:
            if m == "wget":
                success = download_with_wget(
                    url,
                    output_dir_path
                    / (name or Path(urlparse(url).path).name or "downloaded_file"),
                    resume,
                    quiet,
                )
            elif m == "curl":
                success = download_with_curl(
                    url,
                    output_dir_path
                    / (name or Path(urlparse(url).path).name or "downloaded_file"),
                    resume,
                    quiet,
                )
            else:
                continue
            if success:
                break
        else:
            error_msg = f"All download methods failed for {url}"
            logger.error(error_msg)
            print(f"❌ {error_msg}", file=sys.stderr)
            continue

        file_path = output_dir_path / (
            name or Path(urlparse(url).path).name or "downloaded_file"
        )
        if file_path.exists():
            size = file_path.stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"📁 File saved: {file_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download files from URLs using aria2c, wget, or curl."
    )
    parser.add_argument("urls", nargs="+", help="One or more URLs to download.")
    parser.add_argument(
        "--output-name", "-n", help="Optional output filename (for single file only)."
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Directory to save the file(s) (default: ~/Downloads).",
    )
    parser.add_argument(
        "--method",
        "-m",
        choices=["auto", "aria2", "wget", "curl"],
        default="auto",
        help="Download method: auto, aria2, wget, curl (default: auto).",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume functionality (default: resume enabled).",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress output (quiet mode)."
    )

    args = parser.parse_args()

    download_files(
        urls=args.urls,
        output_name=args.output_name,
        output_dir=args.output_dir,
        method=args.method,
        resume=not args.no_resume,
        quiet=args.quiet,
    )
