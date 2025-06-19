#!/usr/bin/env python3
"""
ChromeDriver Auto-Installer
--------------------------
Automatically detects the installed Brave/Chrome/Chromium browser version
and downloads the appropriate ChromeDriver to match.

Usage: sudo python3 install_chromedriver.py [--force] [--browser chrome|brave|chromium] [--dry-run]
"""

import os
import re
import sys
import json
import shutil
import logging
import zipfile
import platform
import argparse
import tempfile
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from helper import setup_logging

logger = setup_logging(log_file="chromedriver_installer.log")


class ChromeDriverInstaller:
    """Handles detection, download and installation of the appropriate ChromeDriver."""

    # Metadata URL for Chrome for Testing
    METADATA_URL = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"

    # Map of operating systems to Chrome for Testing platform names
    PLATFORM_MAP = {
        "linux": "linux64",
        "darwin": "mac-x64" if platform.machine() != "arm64" else "mac-arm64",
        "win32": "win32",
        "win64": "win64",
    }

    # Browser executable names by platform and browser type
    BROWSER_EXECUTABLES = {
        "linux": {
            "chrome": ["google-chrome", "chrome"],
            "brave": ["brave-browser"],
            "chromium": ["chromium-browser", "chromium"],
        },
        "darwin": {
            "chrome": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
            "brave": ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
            "chromium": ["/Applications/Chromium.app/Contents/MacOS/Chromium"],
        },
        "win32": {
            "chrome": [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            ],
            "brave": [
                "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                "C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            ],
            "chromium": [
                "C:\\Program Files\\Chromium\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Chromium\\Application\\chrome.exe",
            ],
        },
    }

    def __init__(
        self,
        browser: str = "brave",
        force: bool = False,
        debug: bool = False,
        dry_run: bool = False,
    ):
        """
        Initialize the ChromeDriver installer.

        Args:
            browser: Browser to detect ('chrome', 'brave', or 'chromium')
            force: Force installation even if ChromeDriver is already installed
            debug: Enable debug logging
            dry_run: If True, show what would be done without actually doing it
        """
        self.browser = browser
        self.force = force
        self.dry_run = dry_run

        if debug:
            logger.setLevel(logging.DEBUG)

        # Detect current platform
        self.system = platform.system().lower()
        if self.system == "windows":
            self.system = "win32" if platform.architecture()[0] == "32bit" else "win64"
        elif self.system == "darwin":
            self.system = "darwin"
        else:
            self.system = "linux"

        # Set installation paths based on platform
        if self.system.startswith("win"):
            self.installation_path = os.path.join(
                os.environ.get("ProgramFiles", "C:\\Program Files"), "ChromeDriver"
            )
            self.executable_path = os.path.join(
                self.installation_path, "chromedriver.exe"
            )
        else:
            self.installation_path = "/usr/local/bin"
            self.executable_path = os.path.join(self.installation_path, "chromedriver")

        logger.debug(f"Detected system: {self.system}")
        logger.debug(f"Installation path: {self.installation_path}")

    def get_browser_version(self) -> Optional[str]:
        """
        Detect the installed browser version.

        Returns:
            Browser version string or None if not detected
        """
        executables = self.BROWSER_EXECUTABLES.get(self.system, {}).get(
            self.browser, []
        )
        if not executables:
            logger.error(f"Unsupported browser '{self.browser}' on {self.system}")
            return None

        for executable in executables:
            try:
                cmd = [executable, "--version"]
                logger.debug(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    logger.debug(f"Command failed with return code {result.returncode}")
                    continue

                version_output = result.stdout.strip()
                logger.debug(f"Version output: {version_output}")

                # Different browsers format their version string differently
                match = re.search(r"(\d+\.\d+\.\d+\.\d+)", version_output)
                if not match:
                    match = re.search(r"(\d+\.\d+\.\d+)", version_output)
                if match:
                    return match.group(1)
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.debug(f"Error running {executable}: {e}")
                continue

        logger.error(
            f"Could not detect {self.browser} version. Make sure it's installed and accessible."
        )
        return None

    def get_matching_chromedriver_version(self, browser_version: str) -> Optional[str]:
        """
        Find the appropriate ChromeDriver version for the detected browser.

        Args:
            browser_version: Detected browser version

        Returns:
            Matching ChromeDriver version or None if not found
        """
        major_version = browser_version.split(".")[0]
        logger.info(
            f"Looking for ChromeDriver version matching browser major version {major_version}"
        )

        try:
            with urllib.request.urlopen(self.METADATA_URL) as response:
                data = json.load(response)

                # First try to find an exact major version match in the Stable channel
                stable_version = data["channels"]["Stable"]["version"]
                if stable_version.startswith(f"{major_version}."):
                    return stable_version

                # Try other channels if Stable doesn't match
                for channel in ["Beta", "Dev", "Canary"]:
                    if channel in data["channels"]:
                        channel_version = data["channels"][channel]["version"]
                        if channel_version.startswith(f"{major_version}."):
                            logger.info(f"Found matching version in {channel} channel")
                            return channel_version

                # If we still can't find a match, try the milestone versions
                if "milestones" in data and major_version in data["milestones"]:
                    return data["milestones"][major_version]["version"]
        except Exception as e:
            logger.error(f"Error fetching ChromeDriver metadata: {e}")

        logger.error(
            f"No matching ChromeDriver version found for browser version {browser_version}"
        )
        return None

    def download_and_install_chromedriver(self, version: str) -> bool:
        """
        Download and install the specified ChromeDriver version.

        Args:
            version: ChromeDriver version to download

        Returns:
            True if installation was successful, False otherwise
        """
        platform_name = self.PLATFORM_MAP.get(self.system)
        if not platform_name:
            logger.error(f"Unsupported platform: {self.system}")
            return False

        base_url = "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing"
        zip_url = (
            f"{base_url}/{version}/{platform_name}/chromedriver-{platform_name}.zip"
        )

        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would download ChromeDriver {version} from {zip_url}"
            )
            logger.info(
                f"[DRY RUN] Would install ChromeDriver to {self.executable_path}"
            )
            return True

        logger.info(f"Downloading ChromeDriver {version} from {zip_url}")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "chromedriver.zip")

                # Download the zip file
                urllib.request.urlretrieve(zip_url, zip_path)

                # Extract the zip file
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Find the chromedriver executable in the extracted files
                if self.system.startswith("win"):
                    chromedriver_name = "chromedriver.exe"
                else:
                    chromedriver_name = "chromedriver"

                chromedriver_dir = os.path.join(
                    temp_dir, f"chromedriver-{platform_name}"
                )
                chromedriver_path = os.path.join(chromedriver_dir, chromedriver_name)

                # Check if the file exists
                if not os.path.exists(chromedriver_path):
                    # Look for it in subdirectories
                    for root, dirs, files in os.walk(temp_dir):
                        if chromedriver_name in files:
                            chromedriver_path = os.path.join(root, chromedriver_name)
                            break

                if not os.path.exists(chromedriver_path):
                    logger.error(
                        f"Could not find {chromedriver_name} in the downloaded archive"
                    )
                    return False

                # Make sure the executable has the right permissions
                if not self.system.startswith("win"):
                    os.chmod(chromedriver_path, 0o755)

                # Create installation directory if it doesn't exist
                os.makedirs(self.installation_path, exist_ok=True)

                # Remove existing chromedriver if it exists
                if os.path.exists(self.executable_path):
                    os.remove(self.executable_path)

                # Install the new chromedriver
                shutil.copy2(chromedriver_path, self.executable_path)
                logger.info(
                    f"Successfully installed ChromeDriver {version} to {self.executable_path}"
                )

                return True
        except Exception as e:
            logger.error(f"Error installing ChromeDriver: {e}")
            return False

    def check_existing_installation(self) -> bool:
        """
        Check if ChromeDriver is already installed and matches the browser version.

        Returns:
            True if a matching installation exists, False otherwise
        """
        if not self.force and os.path.exists(self.executable_path):
            try:
                if self.dry_run:
                    logger.info(
                        f"[DRY RUN] Would check existing ChromeDriver at {self.executable_path}"
                    )
                    # In dry-run mode, pretend we don't have a matching version so we can show the full process
                    return False

                cmd = [self.executable_path, "--version"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    chromedriver_version = result.stdout.strip()
                    match = re.search(
                        r"ChromeDriver (\d+\.\d+\.\d+)", chromedriver_version
                    )
                    if match:
                        driver_major = match.group(1).split(".")[0]
                        browser_version = self.get_browser_version()
                        if browser_version:
                            browser_major = browser_version.split(".")[0]
                            if driver_major == browser_major:
                                logger.info(
                                    f"Existing ChromeDriver installation (version {match.group(1)}) "
                                    f"matches browser major version {browser_major}"
                                )
                                return True
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.debug(f"Error checking existing ChromeDriver: {e}")

        return False

    def run(self) -> int:
        """
        Run the ChromeDriver installation process.

        Returns:
            0 on success, non-zero on failure
        """
        # Check if an existing installation is sufficient
        if self.check_existing_installation():
            if not self.force:
                logger.info("Using existing ChromeDriver installation")
                return 0
            logger.info("Forcing reinstallation of ChromeDriver")

        # Detect browser version
        browser_version = self.get_browser_version()
        if not browser_version:
            return 1

        logger.info(f"Detected {self.browser.capitalize()} version: {browser_version}")

        # Find matching ChromeDriver version
        chromedriver_version = self.get_matching_chromedriver_version(browser_version)
        if not chromedriver_version:
            return 1

        logger.info(f"Selected ChromeDriver version: {chromedriver_version}")

        # Download and install ChromeDriver
        if self.dry_run:
            logger.info("[DRY RUN] Installation simulation successful")
            return 0

        if self.download_and_install_chromedriver(chromedriver_version):
            return 0
        return 1


def main():
    """Main function to parse arguments and run the installer."""
    parser = argparse.ArgumentParser(description="ChromeDriver Auto-Installer")
    parser.add_argument(
        "--browser",
        choices=["chrome", "brave", "chromium"],
        default="brave",
        help="Browser to detect (default: brave)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force installation even if already installed",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually installing anything",
    )
    args = parser.parse_args()

    # Check for root privileges on Unix-like systems
    if not args.dry_run and platform.system() != "Windows" and os.geteuid() != 0:
        logger.error(
            "Please run this script with sudo: `sudo python3 install_chromedriver.py`"
        )
        return 1

    if args.dry_run:
        logger.info("Running in dry-run mode - no changes will be made")

    installer = ChromeDriverInstaller(
        browser=args.browser, force=args.force, debug=args.debug, dry_run=args.dry_run
    )
    return installer.run()


if __name__ == "__main__":
    sys.exit(main())
