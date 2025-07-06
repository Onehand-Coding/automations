import os
import re
import sys
import shutil
import argparse
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Union
from collections import defaultdict
from itertools import combinations, zip_longest

from send2trash import send2trash

from helper import new_filepath, setup_logging

# Constants
TO_REPLACE_PATTERN = re.compile(r"\[.*\]|\(.*\)")
SPLIT_PATTERN = re.compile(r"\s+|[.,:_-]")

logger = setup_logging(log_file="file_organizer.log")


class FileTypes(Enum):
    """Enum for different file types and their extensions."""

    VIDEO = (".mp4", ".mkv", ".webm", ".3gp")
    AUDIO = (".mp3", ".m4a", ".wav")
    IMAGE = (".jfif", ".jpg", ".png", ".jpeg", ".gif")
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
    )
    TEXT = (".html", ".css", ".js", ".py", ".txt", ".csv", ".json")
    ARCHIVE = (".zip", ".tar", ".7z", ".rar", ".gz")


class FileOrganizer:
    """Class to organize files in a directory."""

    def __init__(
        self,
        to_sort_path: Union[str, Path],
        to_exclude_files: Optional[List[str]] = None,
    ):
        """Initialize FileOrganizer.

        Args:
            to_sort_path: Path to the directory to organize
            to_exclude_files: List of files or folders to exclude from organization
        """
        self.to_sort_path = Path(to_sort_path)
        self.to_exclude_files = to_exclude_files or []

        if not isinstance(self.to_exclude_files, list):
            raise TypeError(
                "to_exclude_files argument must be a list of file or folder names!"
            )

        self.destination_folders = set()

    def map_file_extensions(self) -> Dict[str, Path]:
        """Map file extensions to their destination folders.

        Returns:
            Dictionary mapping file extensions to destination folders
        """
        # Create mapping of file types to destination folders
        default_paths = {
            file_type: self.to_sort_path / f"{file_type.name.title()} files"
            for file_type in FileTypes
        }

        # Create a defaultdict that returns "Others" path for unknown extensions
        mapped_files = defaultdict(lambda: self.to_sort_path / "Others")

        # Map each file extension to its type's path
        for file in self.get_files():
            for file_type, path in default_paths.items():
                if file.suffix.lower() in file_type.value:
                    mapped_files[file.suffix] = path
                    break

        return mapped_files

    def should_exclude(self, file: Path) -> bool:
        """Check if a file or folder should be excluded.

        Args:
            file: Path to check

        Returns:
            True if the file should be excluded, False otherwise
        """
        return any(to_exclude in file.parts for to_exclude in self.to_exclude_files)

    def get_folders(self) -> List[Path]:
        """Get all folders in the directory to sort.

        Returns:
            List of folders not excluded
        """
        return [
            folder
            for folder in self.to_sort_path.rglob("*/")
            if not self.should_exclude(folder)
        ]

    def get_files(self, folder: Optional[Path] = None) -> List[Path]:
        """Get all files in the directory to sort or in a specific folder.

        Args:
            folder: Optional specific folder to get files from

        Returns:
            List of files not excluded
        """
        if folder is not None:
            return [
                file
                for file in folder.glob("*")
                if file.is_file() and not self.should_exclude(file)
            ]

        return [
            Path(root) / file
            for root, _, files in os.walk(self.to_sort_path)
            for file in files
            if not self.should_exclude(Path(root) / file)
        ]

    @staticmethod
    def move_file(file: Path, dest: Path) -> None:
        """Move a file to a destination folder.

        Args:
            file: File to move
            dest: Destination folder
        """
        # Handle case where destination is a file
        if dest.exists() and dest.is_file():
            logger.debug(
                "Destination folder has the same name as the file. Using file parent as destination..."
            )
            dest = dest.parent

        # Create destination path and ensure destination folder exists
        destination_file = dest / file.name
        dest.mkdir(parents=True, exist_ok=True)

        # Handle file name conflicts
        if destination_file.exists() and not destination_file.samefile(file):
            destination_file = new_filepath(destination_file, add_prefix="_Duplicate")

        # Move the file
        if not destination_file.exists():
            logger.debug(f"Moving {file} to {dest}")
            try:
                shutil.move(str(file), str(destination_file))
            except FileNotFoundError:
                logger.warning(f"Not moved: {file}, This file may be deleted.")

    def type_sort(self) -> None:
        """Sort files by their type (extension)."""
        unsorted_files = self.get_files()
        mapped_files = self.map_file_extensions()

        for file in unsorted_files:
            # Get destination folder by file type
            type_dest = mapped_files[file.suffix]

            # Create subfolder for specific extension
            ext_name = file.suffix.strip(".") if file.suffix else "unknown"
            ext_dest = type_dest / f"{ext_name} files"

            # Move file and update destination folders set
            self.move_file(file, ext_dest)
            self.destination_folders.update({type_dest, ext_dest})

    def prefix_sort(self, folder: Path) -> None:
        """Sort files by their prefix.

        Args:
            folder: Folder containing files to sort
        """
        unsorted_files = self.get_files(folder)
        if not unsorted_files:
            return

        # Group files by prefix
        prefix_folders = defaultdict(list)
        for file in unsorted_files:
            prefix = get_split_stem(SPLIT_PATTERN, TO_REPLACE_PATTERN, file.stem)[0]
            prefix_folders[prefix].append(file)

        # Move files to prefix folders if there are multiple prefixes with multiple files
        if len(prefix_folders) > 1:
            for prefix, files in prefix_folders.items():
                if len(files) > 1:
                    for file in files:
                        if prefix not in file.parts:
                            prefix_folder = file.parent / prefix
                            self.move_file(file, prefix_folder)
                            self.destination_folders.add(prefix_folder)

    def stem_sort(self, folder: Path) -> None:
        """Sort files by common stems in their names.

        Args:
            folder: Folder containing files to sort
        """
        unsorted_files = self.get_files(folder)
        if not unsorted_files:
            return

        common_stems = get_common_stems(unsorted_files)
        if not common_stems:
            return

        file_stems = [
            get_split_stem(SPLIT_PATTERN, TO_REPLACE_PATTERN, file.stem)
            for file in unsorted_files
        ]

        # Group files by common stem
        stem_folders = defaultdict(list)
        for file, file_stem in zip(unsorted_files, file_stems):
            for common_stem in common_stems:
                if len(common_stem) <= len(file_stem) and all(
                    x == y for x, y in zip(common_stem, file_stem)
                ):
                    stem_folders[" ".join(common_stem).strip()].append(file)

        # Move files to stem folders if there are multiple stems with multiple files
        if len(stem_folders) > 1:
            # Sort by stem length in descending order to prioritize more specific stems
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

    def simple_sort(self) -> None:
        """Perform a simple sort by file extension and prefix."""
        unsorted_files = self.get_files(self.to_sort_path)
        existing_folders = set(self.to_sort_path.glob("*/"))

        logger.info("Running simple sort...")
        # Sort by extension
        for file in unsorted_files:
            ext_name = file.suffix.strip(".") if file.suffix else "unknown"
            ext_dest = file.parent / f"{ext_name} files"
            self.move_file(file, ext_dest)

        logger.info("Running prefix_sort...")
        # Sort by prefix in newly created folders
        new_folders = set(self.to_sort_path.glob("*/")) - existing_folders
        for folder in new_folders:
            self.prefix_sort(folder)

        logger.info("Verifying files...")
        verify_files(unsorted_files, self.get_files(self.to_sort_path), method="Simple")

    def recursive_sort(self) -> None:
        """Perform a recursive sort by type, prefix, and stem."""
        unsorted_files = self.get_files()

        logger.info("Running type_sort...")
        self.type_sort()

        logger.info("Running prefix_sort...")
        for folder in self.get_folders():
            self.prefix_sort(folder)

        logger.info("Running stem_sort...")
        for folder in self.get_folders():
            self.stem_sort(folder)

        # Remove empty folders
        empty_folders = set(self.get_folders()) - self.destination_folders
        remove_folders(empty_folders)

        logger.info("Verifying files...")
        verify_files(
            unsorted_files, self.get_files(), empty_folders, method="Aggressive"
        )


def verify_files(
    unsorted_files: List[Path],
    sorted_files: List[Path],
    empty_folders: Optional[Set[Path]] = None,
    *,
    method: str = "",
) -> None:
    """Verify that all files were correctly sorted.

    Args:
        unsorted_files: List of files before sorting
        sorted_files: List of files after sorting
        empty_folders: Set of empty folders that were removed
        method: Method name used for sorting (for logger)
    """
    if empty_folders is None:
        empty_folders = set()

    # Create sets of filenames for comparison
    unsorted_filenames = {file.name for file in unsorted_files}
    sorted_filenames = {file.name for file in sorted_files}

    # Find files that were accidentally deleted
    removed_filenames = unsorted_filenames - sorted_filenames
    if removed_filenames:
        logger.error("Files were included during folder deletion!")
        for filename in removed_filenames:
            try:
                # Find the original file and the folder it was in
                original_file = next(
                    file for file in unsorted_files if file.name == filename
                )
                deleted_folder = next(
                    folder.name
                    for folder in empty_folders
                    if any(part in original_file.parts for part in folder.parts)
                )
                logger.warning(
                    f"Deleted file: {filename} from Folder: {deleted_folder}"
                )
            except (StopIteration, IndexError):
                logger.warning(
                    f"Deleted file: {filename}, unable to determine containing folder"
                )

        logger.error(
            f"{method.title()} sorting finished with error! {len(removed_filenames)} were accidentally deleted, check your trash bin."
        )

    if len(unsorted_filenames) == len(sorted_filenames):
        logger.info("File verification Done! No accidental deletion occured.")
        logger.info(f"{method} file organization successful!")


def remove_folders(folders: Set[Path]) -> None:
    """Move empty folders to trash.

    Args:
        folders: Set of folders to remove
    """
    if not folders:
        return

    logger.info("Moving empty folders to trash...")
    for folder in folders:
        logger.debug(f"Moving {folder} to trash...")
        try:
            send2trash(str(folder))
        except Exception as e:
            logger.error(f"Error removing folder {folder}: {e}")


def split_stem(split_pattern: re.Pattern, stem: str) -> List[str]:
    """Split a file stem using a regex pattern.

    Args:
        split_pattern: Regex pattern to split by
        stem: File stem to split

    Returns:
        List of stem parts
    """
    return [part for part in re.split(split_pattern, stem) if part]


def clean_stem(to_replace_pattern: re.Pattern, stem: str, replacement: str = "") -> str:
    """Clean a file stem by removing patterns.

    Args:
        to_replace_pattern: Regex pattern to replace
        stem: File stem to clean
        replacement: String to replace matches with

    Returns:
        Cleaned stem
    """
    return re.sub(to_replace_pattern, replacement, stem).strip()


def get_split_stem(
    split_pattern: re.Pattern, to_replace_pattern: re.Pattern, stem: str
) -> List[str]:
    """Clean and split a file stem.

    Args:
        split_pattern: Regex pattern to split by
        to_replace_pattern: Regex pattern to replace
        stem: File stem to process

    Returns:
        List of processed stem parts
    """
    cleaned_stem = clean_stem(to_replace_pattern, stem)
    return split_stem(split_pattern, cleaned_stem)


def get_common_stems(files: List[Path]) -> List[List[str]]:
    """Find common stems among file names.

    Args:
        files: List of files to analyze

    Returns:
        List of common stem word sequences
    """
    if len(files) < 2:
        return []

    # Split all file stems
    file_stems = [
        get_split_stem(SPLIT_PATTERN, TO_REPLACE_PATTERN, file.stem) for file in files
    ]

    # Find common stems between all pairs of files
    common_stems = []
    for stem1, stem2 in combinations(file_stems, 2):
        # Find common words in the same positions
        common_words = [
            x
            for x, y in zip_longest(stem1, stem2, fillvalue=None)
            if x == y and x is not None
        ]
        if common_words:
            common_stems.append(tuple(common_words))

    # Remove duplicates and filter out single-word stems
    common_stems = list(set(common_stems))
    return [
        list(common_stem)
        for common_stem in common_stems
        if common_stem and len(set(common_stem)) > 1
    ]


def main() -> None:
    """Main function to run the file organizer."""
    parser = argparse.ArgumentParser(
        description="File Organizer tool with simple and recursive file sorting method.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "folder_path",
        help="Absolute path for folder you wish to organize the files from.",
    )
    parser.add_argument(
        "--method",
        "-m",
        choices=["simple", "recursive"],
        help="Sorting method to use",
        default="recursive",
    )

    args = parser.parse_args()

    # Set the default sorting method to recursive if not specified.
    if not args.method:
        args.method = "recursive"
    logger.info(f"Starting File organizer tool using '{args.method}' method.")

    # Get path to sort
    folder_path = args.folder_path
    organizer = FileOrganizer(folder_path)

    # Get sorting method
    if args.method == "recursive":
        organizer.recursive_sort()
    elif args.method == "simple":
        organizer.simple_sort()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Script Interrupted.")
        sys.exit()
