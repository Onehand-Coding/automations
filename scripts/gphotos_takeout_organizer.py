#!/usr/bin/env python3

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
from datetime import timezone

from helper import LOG_DIR

# --- Constants ---
SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".heic",
    ".bmp",
    ".tiff",
    ".tif",
}
SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".wmv",
    ".mkv",
    ".webm",
    ".mpg",
    ".mpeg",
    ".3gp",
}
SUPPORTED_MEDIA_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS.union(
    SUPPORTED_VIDEO_EXTENSIONS
)
LOG_FILENAME = LOG_DIR / "metadata_embedder.log"

# --- Logging Setup ---
# Basic configuration will be refined in main() based on args.verbose
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
# Set the base level for the logger low enough to capture everything for the file
# We'll adjust level and add console handler later based on verbosity.
logger.setLevel(logging.DEBUG)  # Set base to DEBUG initially

# File handler (always logs at least INFO level to the file, overwrites each run)
file_handler = logging.FileHandler(LOG_FILENAME, mode="w")
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)  # File log gets INFO+
logger.addHandler(file_handler)

# Console handler (configure now, but add to logger *only* if verbose)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
# Default level for console if added (will be set lower if verbose)
console_handler.setLevel(logging.INFO)
# *** DO NOT add console_handler to logger here ***

# --- Helper Functions ---


def is_exiftool_installed():
    """Checks if exiftool is installed and accessible in the system PATH."""
    return shutil.which("exiftool") is not None


def find_media_files(root_dir: Path):
    """Recursively finds all supported media files in the root directory."""
    # This message goes to file, and console if verbose
    logger.info(f"Searching for media files in: {root_dir}")
    media_files = []
    for ext in SUPPORTED_MEDIA_EXTENSIONS:
        media_files.extend(list(root_dir.rglob(f"*{ext}")))
        media_files.extend(
            list(root_dir.rglob(f"*{ext.upper()}"))
        )  # Handle uppercase extensions too

    # Remove duplicates and sort
    unique_media_files = sorted(list(set(media_files)))
    # This message goes to file, and console if verbose
    logger.info(f"Found {len(unique_media_files)} potential media files.")
    return unique_media_files


def find_matching_json(media_path: Path):
    """
    Finds the corresponding JSON metadata file for a given media file.
    Includes handling for common Google Photos naming patterns and OSError 36.
    Priority:
    1. Exact Match: <media_filename>.json
    2. Edited Match: <media_filename_no_ext>(edited).<ext>.json
    3. Numbered Suffix 1: <media_filename_no_ext>(#).<ext>.json
    4. Numbered Suffix 2: <media_filename>.json(#).json (Older pattern)
    5. General Suffix Match: <media_filename>.<any_suffix>.json (e.g., .supplemental-metadata.json)
    """
    parent_dir = media_path.parent
    media_name_no_ext = media_path.stem  # Filename without extension

    # Construct potential JSON paths/names
    exact_json_name = f"{media_path.name}.json"
    exact_json_path = parent_dir / exact_json_name
    edited_json_name = f"{media_name_no_ext}(edited){media_path.suffix}.json"
    edited_json_path = parent_dir / edited_json_name
    numbered_suffix_pattern = f"{media_name_no_ext}(*){media_path.suffix}.json"
    old_numbered_pattern = f"{media_path.name}(*).json"
    general_suffix_pattern = (
        f"{media_path.stem}.*.json"  # Use stem for general match base
    )

    try:
        # 1. Exact Match Check
        if exact_json_path.is_file():
            logger.debug(
                f"Found exact JSON match for {media_path.name}: {exact_json_path.name}"
            )
            return exact_json_path

        # 2. Edited Match Check
        if edited_json_path.is_file():
            logger.debug(
                f"Found edited JSON match for {media_path.name}: {edited_json_path.name}"
            )
            return edited_json_path

        # 3. Numbered Suffix 1 Check (e.g., file(1).jpg.json)
        numbered_matches = sorted(list(parent_dir.glob(numbered_suffix_pattern)))
        if numbered_matches:
            # Basic check: ensure the found name starts correctly and has the number part
            expected_start = f"{media_name_no_ext}("
            valid_numbered = [
                p for p in numbered_matches if p.name.startswith(expected_start)
            ]
            if valid_numbered:
                logger.debug(
                    f"Found numbered suffix JSON match (pattern 1) for {media_path.name}: {valid_numbered[0].name}"
                )
                return valid_numbered[0]

        # 4. Numbered Suffix 2 Check (e.g., file.jpg(1).json) - Older pattern
        old_numbered_matches = sorted(list(parent_dir.glob(old_numbered_pattern)))
        # Filter out the exact match name if it somehow matches the glob
        old_numbered_matches = [
            p for p in old_numbered_matches if p.name != exact_json_name
        ]
        if old_numbered_matches:
            logger.debug(
                f"Found numbered suffix JSON match (pattern 2) for {media_path.name}: {old_numbered_matches[0].name}"
            )
            return old_numbered_matches[0]

        # 5. General Suffix Match (Fallback, e.g., .supplemental-metadata.json)
        potential_matches = sorted(list(parent_dir.glob(general_suffix_pattern)))
        # Filter out ones already checked to avoid duplicates
        checked_paths = {exact_json_path, edited_json_path}
        checked_paths.update(numbered_matches)  # Add Path objects from list
        checked_paths.update(old_numbered_matches)  # Add Path objects from list

        # Find the first potential match not already covered by more specific patterns
        for p in potential_matches:
            is_checked = False
            for checked in checked_paths:
                # Need to compare Path objects or their string representations
                if p.resolve() == checked.resolve():
                    is_checked = True
                    break
            if not is_checked:
                # Check if it's a valid file before returning
                if p.is_file():
                    logger.debug(
                        f"Found general suffix JSON match for {media_path.name}: {p.name}"
                    )
                    return p
                else:
                    # Log if glob finds something that isn't a file (like a dir named .json)
                    logger.debug(f"Ignoring non-file glob match: {p.name}")

    except OSError as e:
        # Handle "File name too long" error specifically
        if e.errno == 36:
            logger.error(
                f"Skipping file due to OS Error (Filename too long): {media_path.name} - Path: {media_path.parent}"
            )
            logger.debug(f"Underlying OS Error: {e}")  # Log full error in debug mode
            return None  # Skip this file
        else:
            # Reraise other OS errors
            logger.error(
                f"An OS error occurred checking JSON for {media_path.name}: {e}"
            )
            raise  # Reraise unexpected OS errors
    except Exception as e:
        # Catch potential unexpected errors during file checks
        logger.error(
            f"An unexpected error occurred finding JSON for {media_path.name}: {e}"
        )
        return None  # Treat as not found

    # If no match found after all checks
    # Log as warning - this will only show on console if verbose
    logger.warning(f"No corresponding JSON found for: {media_path.name}")
    return None


def embed_metadata(media_path: Path, json_path: Path, dry_run: bool):
    """
    Embeds metadata from the JSON file into the media file using exiftool.
    Prioritizes setting specific date/time tags from photoTakenTime.timestamp.
    Includes support for large files.
    Returns True on success, False on failure.
    """
    # This message goes to file, and console if verbose
    logger.info(
        f"Attempting to embed metadata from {json_path.name} into {media_path.name}"
    )

    if not json_path.is_file():
        # Error goes to file, and console if verbose
        logger.error(f"JSON file not found during embed attempt: {json_path}")
        return False

    # Load JSON data to extract timestamp
    metadata = None
    formatted_date = None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        logger.debug(f"Successfully parsed JSON: {json_path.name}")  # Debug level

        # Extract and format the primary timestamp
        if "photoTakenTime" in metadata and "timestamp" in metadata.get(
            "photoTakenTime", {}
        ):
            timestamp_str = metadata["photoTakenTime"]["timestamp"]
            try:
                timestamp_int = int(timestamp_str)
                # Convert Unix timestamp (UTC) to datetime object using timezone-aware method
                dt_object = datetime.fromtimestamp(
                    timestamp_int, timezone.utc
                )  # FIX for DeprecationWarning
                # Format for exiftool (-d '%Y:%m:%d %H:%M:%S' is implicit default for assignments)
                formatted_date = dt_object.strftime("%Y:%m:%d %H:%M:%S")
                logger.debug(
                    f"Extracted photoTakenTime for {media_path.name}: {formatted_date}"
                )
            except (ValueError, TypeError) as ts_err:
                logger.warning(
                    f"Could not parse timestamp '{timestamp_str}' from {json_path.name}: {ts_err}"
                )
                formatted_date = None
        else:
            logger.warning(
                f"JSON file {json_path.name} does not contain 'photoTakenTime.timestamp'. Will rely on basic -tagsFromFile for dates."
            )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file {json_path.name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reading JSON file {json_path.name}: {e}")
        return False

    if dry_run:
        if formatted_date:
            # Info message goes to file, and console if verbose
            logger.info(
                f"[DRY RUN] Would embed metadata from {json_path.name} into {media_path.name}, setting dates to {formatted_date}"
            )
        else:
            logger.info(
                f"[DRY RUN] Would attempt generic embed from {json_path.name} into {media_path.name} (no specific date extracted)"
            )
        return True  # Simulate success in dry run

    try:
        # Base command - always try to pull tags generally
        cmd = [
            "exiftool",
            "-charset",
            "UTF-8",
            "-api",
            "LargeFileSupport=1",  # <<<--- FIX for large file error
            "-tagsFromFile",
            str(json_path),
        ]

        # If we have a specific date, add explicit tag assignments.
        # These will overwrite any conflicting date tags pulled by -tagsFromFile.
        if formatted_date:
            date_tags = [
                # Standard EXIF/XMP tags (useful for images and some video containers)
                f"-DateTimeOriginal={formatted_date}",
                f"-CreateDate={formatted_date}",
                f"-ModifyDate={formatted_date}",
                # QuickTime/MP4 specific tags (important for videos)
                f"-TrackCreateDate={formatted_date}",
                f"-TrackModifyDate={formatted_date}",
                f"-MediaCreateDate={formatted_date}",
                f"-MediaModifyDate={formatted_date}",
            ]
            cmd.extend(date_tags)
            # Note: ExifTool might automatically adjust for timezone based on tag type,
            # or write as UTC. Forcing a timezone offset requires more complex tag syntax.
            # Using the UTC timestamp directly is usually the most reliable starting point.

        # Add final options
        cmd.extend(
            [
                "-overwrite_original",  # Modify file in place
                "-P",  # Preserve original file modification time (of the media file itself)
                str(media_path),  # The target media file
            ]
        )

        # Debug message goes to file, and console if verbose
        logger.debug(f"Running exiftool command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, encoding="utf-8"
        )

        if result.returncode == 0:
            # Check stdout for common "1 image files updated" message
            # Allow for "0 image files updated" if only non-standard tags existed in json
            # or if the specific date tags were already correct. Focus on stderr for real errors.
            if "1 image files updated" in result.stdout:
                # Info message goes to file, and console if verbose
                logger.info(f"Successfully embedded metadata into {media_path.name}")
            else:
                # Log potentially unchanged files or other messages as debug info
                logger.debug(
                    f"Exiftool ran for {media_path.name}. Output: {result.stdout.strip()}"
                )

            # Also log warnings from stderr even on success (return code 0)
            if result.stderr and result.stderr.strip():
                # Filter out ignorable warnings if necessary, e.g., minor conformity warnings
                # For now, log all stderr warnings
                logger.warning(
                    f"Exiftool potential warnings for {media_path.name}: {result.stderr.strip()}"
                )
            return True
        else:
            # Log failures
            log_level = (
                logging.ERROR
            )  # Treat any non-zero exit code as error for simplicity
            # Warning/Error messages go to file, and console if verbose
            logger.log(
                log_level,
                f"Exiftool command failed for {media_path.name} (exit code {result.returncode})",
            )
            if result.stdout and result.stdout.strip():
                logger.log(log_level, f"Exiftool STDOUT:\n{result.stdout.strip()}")
            if result.stderr and result.stderr.strip():
                logger.log(log_level, f"Exiftool STDERR:\n{result.stderr.strip()}")
            return False

    except FileNotFoundError:
        logger.error(
            "Exiftool command not found. Please ensure exiftool is installed and in your system's PATH."
        )
        # Also print critical error to console always
        print(
            "ERROR: Exiftool command not found. Please ensure exiftool is installed and in your system's PATH.",
            file=sys.stderr,
        )
        return False  # Indicate failure
    except subprocess.TimeoutExpired:
        logger.error(f"Exiftool command timed out for {media_path.name}")
        return False
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while running exiftool for {media_path.name}: {e}"
        )
        return False


def delete_file(file_path: Path, dry_run: bool):
    """Safely deletes a file, handling dry run."""
    if dry_run:
        # Info message goes to file, and console if verbose
        logger.info(f"[DRY RUN] Would delete file: {file_path}")
        return True

    try:
        file_path.unlink()
        # Info message goes to file, and console if verbose
        logger.info(f"Successfully deleted file: {file_path}")
        return True
    except OSError as e:
        # Error message goes to file, and console if verbose
        logger.error(f"Failed to delete file {file_path}: {e}")
        return False
    except Exception as e:
        # Error message goes to file, and console if verbose
        logger.error(f"An unexpected error occurred deleting file {file_path}: {e}")
        return False


# --- Main Execution ---


def main():
    parser = argparse.ArgumentParser(
        description="Embed metadata from Google Photos Takeout JSON files into corresponding media files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "takeout_dir",
        type=str,
        help="Path to the root of extracted Google Photos Takeout directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process without modifying or deleting any files.",
    )
    parser.add_argument(
        "--delete-json",
        action="store_true",
        help="Delete JSON files after successfully embedding metadata (prompts for confirmation).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed logs (INFO+) to the console in addition to the log file.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Automatically confirm JSON deletion (use with caution!).",
    )

    args = parser.parse_args()

    # --- Conditional Console Logging Setup ---
    if args.verbose:
        # Set console handler level to show INFO and higher (or DEBUG if you prefer)
        console_handler.setLevel(logging.INFO)
        # Add the console handler to the logger
        logger.addHandler(console_handler)
        # Log that verbose is active (goes to file and console)
        logger.info("Verbose mode enabled. INFO+ logs will be shown on console.")
    else:
        # Ensure logger level is INFO if not verbose (for file handler)
        # Note: Logger base level is already DEBUG, file handler is INFO.
        # We simply don't add the console handler.
        pass  # No action needed, console handler is not added

    # --- Initial Logging ---
    # These messages always go to the file log via file_handler.
    # They only go to the console if console_handler was added (i.e., if verbose).
    logger.info("=" * 30)
    logger.info("Starting Metadata Embedding Process")
    logger.info(f"Takeout Directory: {args.takeout_dir}")
    logger.info(f"Dry Run: {'Yes' if args.dry_run else 'No'}")
    logger.info(f"Delete JSON: {'Yes' if args.delete_json else 'No'}")
    logger.info(f"Verbose: {'Yes' if args.verbose else 'No'}")
    logger.info(f"Log File: {LOG_FILENAME}")
    logger.info("=" * 30)

    # --- Check Exiftool ---
    if not is_exiftool_installed():
        logger.error("Exiftool is not installed or not found in the system PATH.")
        logger.error("Please install exiftool: https://exiftool.org/install.html")
        # Print critical error to console regardless of verbosity
        print("ERROR: Exiftool not found. Please install exiftool.", file=sys.stderr)
        sys.exit(1)
    else:
        # This only shows on console if verbose
        logger.info("Exiftool found.")

    # --- Validate Input Directory ---
    root_dir = Path(args.takeout_dir)
    if not root_dir.is_dir():
        logger.error(
            f"Error: Takeout directory not found or is not a directory: {root_dir}"
        )
        # Print critical error to console regardless of verbosity
        print(
            f"ERROR: Takeout directory not found or is not a directory: {root_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Confirmation for Deletion ---
    confirm_delete = False
    if args.delete_json and not args.dry_run:
        if args.yes:
            # Warning goes to file, and console if verbose
            logger.warning("Automatic confirmation enabled for JSON deletion.")
            confirm_delete = True
        else:
            try:
                # Use print for interactive prompt, always shown on console
                response = (
                    input(
                        "WARNING: You requested to delete JSON files after successful embedding.\n"
                        "This action CANNOT be undone. Are you sure? (yes/no): "
                    )
                    .lower()
                    .strip()
                )
                if response in ("yes", "y"):
                    confirm_delete = True
                    # Info goes to file, and console if verbose
                    logger.info("User confirmed JSON deletion.")
                else:
                    # Warning goes to file, and console if verbose
                    logger.warning("JSON deletion cancelled by user.")
                    args.delete_json = False  # Disable deletion
            except EOFError:
                logger.error(
                    "Cannot confirm JSON deletion in non-interactive mode without --yes flag."
                )
                # Print critical error to console always
                print(
                    "ERROR: Cannot confirm JSON deletion in non-interactive mode without --yes flag.",
                    file=sys.stderr,
                )
                sys.exit(1)

    # --- Find Files ---
    media_files = find_media_files(root_dir)
    if not media_files:
        # Warning goes to file, and console if verbose
        logger.warning("No supported media files found in the specified directory.")
        # Print message to console always
        print("No supported media files found.")
        sys.exit(0)

    # --- Process Files ---
    processed_count = 0
    embedded_count = 0
    json_deleted_count = 0
    json_not_found_count = 0
    error_count = 0
    skipped_unsupported = 0  # Should remain 0 with current logic but good to keep

    try:
        # --- TQDM Setup ---
        # Progress bar always shown on console (stderr)
        pbar = tqdm(media_files, desc="Processing files", unit="file", leave=True)

        for media_file in pbar:
            # Update progress bar description (stderr)
            pbar.set_description(f"Processing {media_file.name[:30]}...")
            # Log detailed processing step (only shows on console if verbose)
            logger.debug(f"Processing media file: {media_file}")

            # Double check extension (already filtered, but safer)
            if media_file.suffix.lower() not in SUPPORTED_MEDIA_EXTENSIONS:
                # Warning goes to file, and console if verbose
                logger.warning(
                    f"Skipping unsupported file format discovered during loop: {media_file}"
                )
                skipped_unsupported += 1
                continue

            processed_count += 1
            json_path = find_matching_json(media_file)

            if json_path:
                # embed_metadata logs its own info/errors/warnings
                if embed_metadata(media_file, json_path, args.dry_run):
                    embedded_count += 1
                    # Delete JSON only if embedding succeeded, deletion requested/confirmed, not dry run
                    if args.delete_json and confirm_delete and not args.dry_run:
                        # delete_file logs its own info/errors
                        if delete_file(json_path, args.dry_run):
                            json_deleted_count += 1
                        else:
                            error_count += 1  # Count deletion failure as an error
                else:
                    # Embedding failed (error already logged inside embed_metadata)
                    error_count += 1
            else:
                # JSON not found (warning already logged inside find_matching_json)
                json_not_found_count += 1

    except KeyboardInterrupt:
        # Warning goes to file, and console if verbose
        logger.warning("Processing interrupted by user.")
        # Print message to console always
        print("\nProcessing interrupted.")
    except Exception as e:
        # Catch unexpected errors during the main loop
        logger.exception(f"An unexpected error occurred during processing: {e}")
        # Print message to console always
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
    finally:
        # Ensure progress bar cleans up properly
        if "pbar" in locals() and pbar:
            pbar.close()

    # --- Summary ---
    # Log summary details (go to file always, console if verbose)
    logger.info("=" * 30)
    logger.info("Processing Summary")
    logger.info(f"Total media files found: {len(media_files)}")
    logger.info(f"Media files processed: {processed_count}")
    logger.info(f"Metadata successfully embedded: {embedded_count}")
    logger.info(f"JSON files successfully deleted: {json_deleted_count}")
    logger.info(f"Media files without matching JSON: {json_not_found_count}")
    logger.info(f"Errors encountered (embedding/deletion): {error_count}")
    logger.info(f"Skipped unsupported files: {skipped_unsupported}")
    logger.info("=" * 30)

    # Print summary to console always using print()
    print("\n--- Processing Summary ---")
    print(f"Total media files found: {len(media_files)}")
    print(f"Media files processed: {processed_count}")
    print(f"Metadata successfully embedded: {embedded_count}")
    # Only show deletion stats if the option was active and not dry run
    if args.delete_json and not args.dry_run:
        print(f"JSON files successfully deleted: {json_deleted_count}")
    print(f"Media files without matching JSON: {json_not_found_count}")
    print(f"Errors encountered (embedding/deletion): {error_count}")
    if skipped_unsupported > 0:
        print(f"Skipped unsupported files: {skipped_unsupported}")
    print(f"Log file generated at: {LOG_FILENAME}")
    if args.dry_run:
        print("\nNOTE: Dry run mode was enabled. No files were modified or deleted.")
    print("-------------------------")


if __name__ == "__main__":
    main()
