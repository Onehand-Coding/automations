#!/usr/bin/env python3
"""
Website Cloner using HTTrack

A robust tool for cloning websites with comprehensive logging and error handling.
Supports multiple URLs and customizable output directories.
"""

import os
import sys
import time
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

from helper import setup_logging


class WebsiteCloner:
    """A robust website cloner using HTTrack with comprehensive logging."""

    def __init__(self, base_output_dir: str, log_level: str = "INFO"):
        """
        Initialize the WebsiteCloner.

        Args:
            base_output_dir: Base directory for cloned websites
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.base_output_dir = Path(base_output_dir).expanduser().resolve()
        self.logger = setup_logging(log_level, log_file="website_cloner.log")
        self._validate_dependencies()
        self._setup_output_directory()

    def _validate_dependencies(self) -> None:
        """Validate that required dependencies are available."""
        self.logger.debug("Validating dependencies...")

        if not shutil.which("httrack"):
            error_msg = (
                "HTTrack is not installed or not in PATH. "
                "Please install HTTrack: https://www.httrack.com/"
            )
            self.logger.critical(error_msg)
            raise RuntimeError(error_msg)

        # Get HTTrack version for logging
        try:
            result = subprocess.run(
                ["httrack", "--version"], capture_output=True, text=True, timeout=10
            )
            version_info = (
                result.stdout.split("\n")[0] if result.stdout else "Unknown version"
            )
            self.logger.info(f"HTTrack found: {version_info}")
        except Exception as e:
            self.logger.warning(f"Could not determine HTTrack version: {e}")

    def _setup_output_directory(self) -> None:
        """Create and validate the base output directory."""
        try:
            self.base_output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Output directory ready: {self.base_output_dir}")

            # Check write permissions
            test_file = self.base_output_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            self.logger.debug("Write permissions confirmed")

        except PermissionError as e:
            error_msg = (
                f"Permission denied creating output directory: {self.base_output_dir}"
            )
            self.logger.critical(error_msg)
            raise PermissionError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to setup output directory: {e}"
            self.logger.critical(error_msg)
            raise RuntimeError(error_msg) from e

    def _sanitize_domain_name(self, domain: str) -> str:
        """
        Sanitize domain name for use as directory name.

        Args:
            domain: Domain name to sanitize

        Returns:
            Sanitized domain name safe for filesystem use
        """
        # Replace problematic characters
        sanitized = domain.replace(".", "_").replace(":", "_").replace("/", "_")
        # Remove any remaining problematic characters
        sanitized = "".join(c for c in sanitized if c.isalnum() or c in "_-")
        return sanitized[:100]  # Limit length

    def _validate_url(self, url: str) -> str:
        """
        Validate and normalize URL.

        Args:
            url: URL to validate

        Returns:
            Normalized URL

        Raises:
            ValueError: If URL is invalid
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                # Add http:// if no scheme provided
                url = f"http://{url}"
                parsed = urlparse(url)
                self.logger.info(f"Added http:// scheme to URL: {url}")

            if not parsed.netloc:
                raise ValueError("URL must have a valid domain")

            # Reconstruct URL to normalize it
            normalized_url = urlunparse(parsed)
            self.logger.debug(f"Normalized URL: {url} -> {normalized_url}")
            return normalized_url

        except Exception as e:
            error_msg = f"Invalid URL '{url}': {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e

    def clone_site(self, url: str, custom_options: Optional[List[str]] = None) -> bool:
        """
        Clone a single website using HTTrack.

        Args:
            url: URL to clone
            custom_options: Additional HTTrack options

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()

        try:
            # Validate and normalize URL
            normalized_url = self._validate_url(url)
            parsed_url = urlparse(normalized_url)
            domain = self._sanitize_domain_name(parsed_url.netloc)

            output_path = self.base_output_dir / domain

            self.logger.info(f"Starting clone: {normalized_url}")
            self.logger.info(f"Output directory: {output_path}")

            # Prepare HTTrack command
            cmd = [
                "httrack",
                normalized_url,
                "-O",
                str(output_path),
                "+*.css",
                "+*.js",
                "+*.html",
                "+*.png",
                "+*.jpg",
                "+*.gif",
                "+*.ico",
                "--display",  # Show progress
                "--robots=0",  # Ignore robots.txt
                "--timeout=60",  # Set timeout
                "--retries=3",  # Number of retries
                "--max-rate=0",  # No rate limiting
            ]

            # Add custom options if provided
            if custom_options:
                cmd.extend(custom_options)
                self.logger.debug(f"Added custom options: {custom_options}")

            self.logger.debug(f"Executing command: {' '.join(cmd)}")

            # Execute HTTrack
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                check=True,
            )

            elapsed_time = time.time() - start_time

            # Log output for debugging
            if process.stdout:
                self.logger.debug(f"HTTrack stdout: {process.stdout}")
            if process.stderr:
                self.logger.warning(f"HTTrack stderr: {process.stderr}")

            # Check if files were actually created
            if output_path.exists() and any(output_path.iterdir()):
                file_count = len(list(output_path.rglob("*")))
                size_mb = sum(
                    f.stat().st_size for f in output_path.rglob("*") if f.is_file()
                ) / (1024 * 1024)

                self.logger.info(
                    f"✅ Successfully cloned {normalized_url} "
                    f"({file_count} files, {size_mb:.1f} MB) "
                    f"in {elapsed_time:.1f}s"
                )
                return True
            else:
                self.logger.error(
                    f"❌ Clone appeared successful but no files were created for {normalized_url}"
                )
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ Timeout cloning {url} (exceeded 1 hour)")
            return False
        except subprocess.CalledProcessError as e:
            elapsed_time = time.time() - start_time
            self.logger.error(
                f"❌ HTTrack failed for {url} (exit code {e.returncode}) "
                f"after {elapsed_time:.1f}s"
            )
            if e.stderr:
                self.logger.error(f"HTTrack error output: {e.stderr}")
            return False
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(
                f"❌ Unexpected error cloning {url} after {elapsed_time:.1f}s: {e}",
                exc_info=True,
            )
            return False

    def clone_multiple_sites(
        self, urls: List[str], custom_options: Optional[List[str]] = None
    ) -> dict:
        """
        Clone multiple websites.

        Args:
            urls: List of URLs to clone
            custom_options: Additional HTTrack options

        Returns:
            Dictionary with results for each URL
        """
        self.logger.info(f"Starting batch clone of {len(urls)} websites")
        start_time = time.time()

        results = {}
        successful = 0

        for i, url in enumerate(urls, 1):
            self.logger.info(f"\n{'=' * 60}")
            self.logger.info(f"Processing {i}/{len(urls)}: {url}")
            self.logger.info(f"{'=' * 60}")

            success = self.clone_site(url, custom_options)
            results[url] = success

            if success:
                successful += 1

        elapsed_time = time.time() - start_time

        # Summary
        self.logger.info(f"\n{'=' * 60}")
        self.logger.info("BATCH CLONE SUMMARY")
        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"Total sites: {len(urls)}")
        self.logger.info(f"Successful: {successful}")
        self.logger.info(f"Failed: {len(urls) - successful}")
        self.logger.info(f"Total time: {elapsed_time:.1f}s")
        self.logger.info(f"Output directory: {self.base_output_dir}")

        return results


def main():
    """Main entry point for the website cloner."""
    parser = argparse.ArgumentParser(
        description="Clone websites using HTTrack with comprehensive logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://docs.python.org
  %(prog)s -d ~/my-docs https://docs.python.org https://flask.palletsprojects.com
  %(prog)s --log-level DEBUG https://example.com
  %(prog)s --httrack-options "--max-rate=1000 --depth=2" https://example.com
        """,
    )

    parser.add_argument(
        "urls", metavar="URL", nargs="+", help="One or more URLs to clone"
    )

    parser.add_argument(
        "-d",
        "--dir",
        help="Base output directory (default: ~/Coding/docs)",
        default="~/Coding/docs",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )

    parser.add_argument(
        "--httrack-options",
        help="Additional HTTrack options (space-separated string)",
        default="",
    )

    args = parser.parse_args()

    try:
        # Parse custom HTTrack options
        custom_options = args.httrack_options.split() if args.httrack_options else None

        # Initialize cloner
        cloner = WebsiteCloner(args.dir, args.log_level)

        # Clone websites
        results = cloner.clone_multiple_sites(args.urls, custom_options)

        # Exit with appropriate code
        failed_count = sum(1 for success in results.values() if not success)
        if failed_count > 0:
            sys.exit(1)  # Some failures occurred
        else:
            sys.exit(0)  # All successful

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
