#!/usr/bin/env python3
import os
import re
import sys
import shutil
import logging
import argparse
from datetime import datetime
from enum import Enum
from pathlib import Path
from collections import defaultdict
from itertools import combinations, zip_longest
from typing import List, Dict, Set, Optional, Union
from dataclasses import dataclass, field

from tqdm import tqdm
from send2trash import send2trash

from helper import new_filepath, setup_logging

# Constants
TO_REPLACE_PATTERN = re.compile(r"\[.*\]|\(.*\)")
SPLIT_PATTERN = re.compile(r"\s+|[.,:_-]")

logger = setup_logging(log_file="file_organizer.log")


@dataclass
class OrganizationStats:
    """Statistics for file organization operations."""

    total_files: int = 0
    moved_files: int = 0
    skipped_files: int = 0
    created_folders: int = 0
    removed_folders: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    method_stats: Dict[str, int] = field(default_factory=dict)

    def duration(self) -> str:
        """Calculate and return formatted duration."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return f"{delta.total_seconds():.2f}s"
        return "N/A"


class FileTypes(Enum):
    """Enum for different file types and their extensions."""

    VIDEO = (".mp4", ".mkv", ".webm", ".3gp", ".avi", ".mov", ".wmv", ".flv")
    AUDIO = (".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".wma")
    IMAGE = (".jfif", ".jpg", ".png", ".jpeg", ".gif", ".bmp", ".tiff", ".svg", ".webp")
    OFFICE = (
        ".docx",
        ".xlsx",
        ".pptx",
        ".pdf",
        ".doc",
        ".xlsm",
        ".pub",
        ".odt",
        ".pptm",
        ".ppsx",
        ".xls",
        ".ppt",
        ".rtf",
        ".pages",
        ".numbers",
        ".key",
    )
    TEXT = (
        ".html",
        ".css",
        ".js",
        ".py",
        ".txt",
        ".csv",
        ".json",
        ".xml",
        ".md",
        ".log",
    )
    ARCHIVE = (
        ".zip",
        ".tar",
        ".7z",
        ".rar",
        ".gz",
        ".bz2",
        ".xz",
        ".tar.gz",
        ".tar.bz2",
    )
    EXECUTABLE = (".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".app")
    FONT = (".ttf", ".otf", ".woff", ".woff2", ".eot")


class SortMethod(Enum):
    """Enum for sorting methods."""

    BY_TYPE = "type"
    BY_EXT = "extension"
    BY_DATE = "date"
    BY_STEM = "name"


class FileOrganizer:
    """Enhanced class to organize files in a directory."""

    def __init__(
        self,
        to_sort_path: Union[str, Path],
        methods: List[SortMethod],
        recursive: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
        to_exclude_files: Optional[List[str]] = None,
    ):
        """Initialize FileOrganizer.

        Args:
            to_sort_path: Path to the directory to organize
            methods: List of sorting methods to apply
            recursive: Whether to sort recursively or just top level
            dry_run: Whether to perform a dry run without actual file operations
            verbose: Whether to enable verbose logging
            to_exclude_files: List of files or folders to exclude from organization
        """
        self.to_sort_path = Path(to_sort_path)
        self.methods = methods
        self.recursive = recursive
        self.dry_run = dry_run
        self.verbose = verbose
        self.to_exclude_files = to_exclude_files or []
        self.stats = OrganizationStats()
        self.destination_folders = set()
        self.progress_bar = None

        if not isinstance(self.to_exclude_files, list):
            raise TypeError(
                "to_exclude_files argument must be a list of file or folder names!"
            )

        # Configure logging level based on verbose flag
        if self.verbose:
            logger.setLevel(logging.DEBUG)

    def log_verbose(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            logger.info(message)

    def update_progress(self, description: str = None) -> None:
        """Update progress bar with optional description."""
        if self.progress_bar:
            if description:
                self.progress_bar.set_description(description)
            self.progress_bar.update(1)

    def map_file_extensions(self) -> Dict[str, Path]:
        """Map file extensions to their destination folders."""
        default_paths = {
            file_type: self.to_sort_path / f"{file_type.name.title()} files"
            for file_type in FileTypes
        }

        mapped_files = defaultdict(lambda: self.to_sort_path / "Others")

        for file in self.get_files():
            for file_type, path in default_paths.items():
                if file.suffix.lower() in file_type.value:
                    mapped_files[file.suffix] = path
                    break

        return mapped_files

    def should_exclude(self, file: Path) -> bool:
        """Check if a file or folder should be excluded."""
        return any(to_exclude in file.parts for to_exclude in self.to_exclude_files)

    def get_folders(self) -> List[Path]:
        """Get all folders in the directory to sort."""
        if self.recursive:
            return [
                folder
                for folder in self.to_sort_path.rglob("*/")
                if not self.should_exclude(folder)
            ]
        else:
            return [
                folder
                for folder in self.to_sort_path.glob("*/")
                if not self.should_exclude(folder)
            ]

    def get_files(self, folder: Optional[Path] = None) -> List[Path]:
        """Get all files in the directory to sort or in a specific folder."""
        if folder is not None:
            return [
                file
                for file in folder.glob("*")
                if file.is_file() and not self.should_exclude(file)
            ]

        if self.recursive:
            return [
                Path(root) / file
                for root, _, files in os.walk(self.to_sort_path)
                for file in files
                if not self.should_exclude(Path(root) / file)
            ]
        else:
            return [
                file
                for file in self.to_sort_path.glob("*")
                if file.is_file() and not self.should_exclude(file)
            ]

    def get_file_date(self, file: Path) -> datetime:
        """Get file modification date."""
        return datetime.fromtimestamp(file.stat().st_mtime)

    def move_file(self, file: Path, dest: Path) -> bool:
        """Move a file to a destination folder.

        Args:
            file: File to move
            dest: Destination folder

        Returns:
            True if file was moved successfully, False otherwise
        """
        if dest.exists() and dest.is_file():
            self.log_verbose(
                f"Destination folder has same name as file. Using parent: {dest.parent}"
            )
            dest = dest.parent

        destination_file = dest / file.name

        if self.dry_run:
            self.log_verbose(f"[DRY RUN] Would move {file} to {dest}")
            return True

        folder_created = not dest.exists()
        dest.mkdir(parents=True, exist_ok=True)
        self.stats.created_folders += 1 if folder_created else 0

        if destination_file.exists() and not destination_file.samefile(file):
            destination_file = new_filepath(destination_file, add_prefix="_Duplicate")

        if not destination_file.exists():
            self.log_verbose(f"Moving {file} to {dest}")
            try:
                shutil.move(str(file), str(destination_file))
                self.stats.moved_files += 1
                return True
            except FileNotFoundError:
                logger.warning(f"Not moved: {file}, file may be deleted.")
                self.stats.errors += 1
                return False
        else:
            self.stats.skipped_files += 1
            return False

    def sort_by_type(self) -> None:
        """Sort files by their type (extension category)."""
        self.log_verbose("Starting sort by type...")
        unsorted_files = self.get_files()
        mapped_files = self.map_file_extensions()

        for file in unsorted_files:
            type_dest = mapped_files[file.suffix]
            self.move_file(file, type_dest)
            self.destination_folders.add(type_dest)
            self.update_progress("Sorting by type")

        self.stats.method_stats["by_type"] = len(unsorted_files)

    def sort_by_extension(self) -> None:
        """Sort files by their specific extension."""
        self.log_verbose("Starting sort by extension...")
        unsorted_files = self.get_files()
        mapped_files = self.map_file_extensions()

        for file in unsorted_files:
            type_dest = mapped_files[file.suffix]
            ext_name = file.suffix.strip(".") if file.suffix else "unknown"
            ext_dest = type_dest / f"{ext_name} files"

            self.move_file(file, ext_dest)
            self.destination_folders.update({type_dest, ext_dest})
            self.update_progress("Sorting by extension")

        self.stats.method_stats["by_ext"] = len(unsorted_files)

    def sort_by_date(self) -> None:
        """Sort files by their modification date."""
        self.log_verbose("Starting sort by date...")
        unsorted_files = self.get_files()

        for file in unsorted_files:
            file_date = self.get_file_date(file)
            year_folder = file.parent / f"{file_date.year}"
            month_folder = (
                year_folder / f"{file_date.month:02d}-{file_date.strftime('%B')}"
            )

            self.move_file(file, month_folder)
            self.destination_folders.update({year_folder, month_folder})
            self.update_progress("Sorting by date")

        self.stats.method_stats["by_date"] = len(unsorted_files)

    def sort_by_name(self, folder: Path = None) -> None:
        """Sort files by common stems in their names."""
        self.log_verbose(f"Starting sort by stem in {folder or 'all folders'}...")
        target_folder = folder or self.to_sort_path

        if self.recursive and folder is None:
            folders_to_process = [self.to_sort_path] + self.get_folders()
        else:
            folders_to_process = [target_folder]

        total_processed = 0
        for current_folder in folders_to_process:
            unsorted_files = self.get_files(current_folder)
            if not unsorted_files:
                continue

            common_stems = get_common_stems(unsorted_files)
            if not common_stems:
                continue

            file_stems = [
                get_split_stem(SPLIT_PATTERN, TO_REPLACE_PATTERN, file.stem)
                for file in unsorted_files
            ]

            stem_folders = defaultdict(list)
            for file, file_stem in zip(unsorted_files, file_stems):
                for common_stem in common_stems:
                    if len(common_stem) <= len(file_stem) and all(
                        x == y for x, y in zip(common_stem, file_stem)
                    ):
                        stem_folders[" ".join(common_stem).strip()].append(file)

            if len(stem_folders) > 1:
                for common_stem in sorted(stem_folders.keys(), key=len, reverse=True):
                    files = stem_folders[common_stem]
                    if len(files) > 1:
                        for file in files:
                            if file.exists() and not set(common_stem.split()) <= set(
                                file.parts
                            ):
                                stem_folder = file.parent / common_stem
                                self.move_file(file, stem_folder)
                                self.destination_folders.add(stem_folder)
                                total_processed += 1
                                self.update_progress("Sorting by stem")

        self.stats.method_stats["by_stem"] = total_processed

    def organize(self) -> OrganizationStats:
        """Main organization method that applies all selected methods."""
        self.stats.start_time = datetime.now()
        self.stats.total_files = len(self.get_files())

        if self.stats.total_files == 0:
            logger.info("No files to organize.")
            return self.stats

        # Store original folders before any organization
        original_folders = set(self.get_folders())

        # Initialize progress bar
        total_operations = self.stats.total_files * len(self.methods)
        self.progress_bar = tqdm(
            total=total_operations, desc="Organizing files", disable=not self.verbose
        )

        logger.info(
            f"Starting organization with methods: {[m.value for m in self.methods]}"
        )
        logger.debug(f"Mode: {'Recursive' if self.recursive else 'Simple'}")
        logger.info(f"Dry run: {self.dry_run}")

        # Apply each method in order
        for method in self.methods:
            if method == SortMethod.BY_TYPE:
                self.sort_by_type()
            elif method == SortMethod.BY_EXT:
                self.sort_by_extension()
            elif method == SortMethod.BY_DATE:
                self.sort_by_date()
            elif method == SortMethod.BY_STEM:
                self.sort_by_name()

        # Remove empty folders if not dry run
        if not self.dry_run:
            # Only remove folders that:
            # 1. Existed before organization, AND
            # 2. Are now empty, AND
            # 3. Are not in our destination folders
            current_folders = set(self.get_folders())
            empty_folders = set()

            for folder in original_folders:
                if folder.exists() and folder not in self.destination_folders:
                    # Check if folder is actually empty
                    if not any(folder.iterdir()):
                        empty_folders.add(folder)

            self.remove_folders(empty_folders)

        self.progress_bar.close()
        self.stats.end_time = datetime.now()

        # Final verification
        if not self.dry_run:
            self.verify_organization()

        return self.stats

    def remove_folders(self, folders: Set[Path]) -> None:
        """Move empty folders to trash."""
        if not folders:
            return

        logger.info("Moving empty folders to trash...")
        for folder in folders:
            self.log_verbose(f"Moving {folder} to trash...")
            try:
                if not self.dry_run:
                    send2trash(str(folder))
                self.stats.removed_folders += 1
            except Exception as e:
                logger.error(f"Error removing folder {folder}: {e}")
                self.stats.errors += 1

    def verify_organization(self) -> None:
        """Verify that organization was successful."""
        logger.info("Verifying organization...")
        current_files = self.get_files()

        if len(current_files) != self.stats.total_files:
            missing_files = self.stats.total_files - len(current_files)
            logger.error(
                f"Organization verification failed! {missing_files} files missing."
            )
            self.stats.errors += missing_files
        else:
            logger.info("Organization verification successful!")

    def print_summary(self) -> None:
        """Print organization summary."""
        print("\n" + "=" * 50)
        print("FILE ORGANIZATION SUMMARY")
        print("=" * 50)
        print(f"Total files processed: {self.stats.total_files}")
        print(f"Files moved: {self.stats.moved_files}")
        print(f"Files skipped: {self.stats.skipped_files}")
        print(f"Folders created: {self.stats.created_folders}")
        print(f"Folders removed: {self.stats.removed_folders}")
        print(f"Errors: {self.stats.errors}")
        print(f"Duration: {self.stats.duration()}")
        print(f"Mode: {'Recursive' if self.recursive else 'Simple'}")
        print(f"Dry run: {self.dry_run}")

        if self.stats.method_stats:
            print("\nMethod Statistics:")
            for method, count in self.stats.method_stats.items():
                print(f"  {method}: {count} files processed")

        print("=" * 50)


def split_stem(split_pattern: re.Pattern, stem: str) -> List[str]:
    """Split a file stem using a regex pattern."""
    return [part for part in re.split(split_pattern, stem) if part]


def clean_stem(to_replace_pattern: re.Pattern, stem: str, replacement: str = "") -> str:
    """Clean a file stem by removing patterns."""
    return re.sub(to_replace_pattern, replacement, stem).strip()


def get_split_stem(
    split_pattern: re.Pattern, to_replace_pattern: re.Pattern, stem: str
) -> List[str]:
    """Clean and split a file stem."""
    cleaned_stem = clean_stem(to_replace_pattern, stem)
    return split_stem(split_pattern, cleaned_stem)


def get_common_stems(files: List[Path]) -> List[List[str]]:
    """Find common stems among file names."""
    if len(files) < 2:
        return []

    file_stems = [
        get_split_stem(SPLIT_PATTERN, TO_REPLACE_PATTERN, file.stem) for file in files
    ]

    common_stems = []
    for stem1, stem2 in combinations(file_stems, 2):
        common_words = [
            x
            for x, y in zip_longest(stem1, stem2, fillvalue=None)
            if x == y and x is not None
        ]
        if common_words:
            common_stems.append(tuple(common_words))

    common_stems = list(set(common_stems))
    return [
        list(common_stem)
        for common_stem in common_stems
        if common_stem and len(set(common_stem)) > 1
    ]


def parse_methods(method_args: List[str]) -> List[SortMethod]:
    """Parse method arguments into SortMethod enum values."""
    methods = []
    for method_str in method_args:
        try:
            method = SortMethod(method_str)
            methods.append(method)
        except ValueError:
            logger.error(f"Invalid method: {method_str}")
            sys.exit(1)
    return methods


def main() -> None:
    """Main function to run the file organizer."""
    parser = argparse.ArgumentParser(
        description="Enhanced File Organizer with multiple sorting methods and options.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "folder_path", help="Absolute path for folder you wish to organize files from."
    )
    parser.add_argument(
        "--method",
        "-m",
        nargs="+",
        choices=[method.value for method in SortMethod],
        default=["type"],
        help="Sorting method(s) to use. Can specify multiple methods.",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        default=False,
        help="Sort files recursively in all subfolders (default: only top-level folder)",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Perform a dry run without actually moving files",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Files or folders to exclude from organization",
    )

    args = parser.parse_args()

    # Use args.recursive directly; default is False (top-level only)
    recursive = args.recursive

    # Parse methods
    methods = parse_methods(args.method)

    logger.info(f"Starting Enhanced File Organizer")
    logger.info(f"Methods: {[m.value for m in methods]}")
    logger.info(f"Recursive: {recursive}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Verbose: {args.verbose}")

    # Create organizer and run
    organizer = FileOrganizer(
        to_sort_path=args.folder_path,
        methods=methods,
        recursive=recursive,
        dry_run=args.dry_run,
        verbose=args.verbose,
        to_exclude_files=args.exclude,
    )

    try:
        stats = organizer.organize()
        organizer.print_summary()

        if stats.errors > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
