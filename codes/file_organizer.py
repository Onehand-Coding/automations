import re
import shutil
import logging
from enum import Enum
from pathlib import Path
from collections import defaultdict
from itertools import combinations, zip_longest

from send2trash import send2trash

from helper import get_folder_path, new_filepath, confirm, configure_logging

LOG_FILE = Path(__file__).parents[1] / 'logs' / 'file_organizer_logs.txt'

TO_REPLACE_PATTERN = re.compile(r'\[.*\]|\(.*\)')
SPLIT_PATTERN = re.compile(r'\s+|[.,:_-]')


class FileType(Enum):
    VIDEO = (".mp4", ".mkv", ".webm", ".3gp")
    AUDIO = (".mp3", ".m4a", ".wav")
    IMAGE = (".jfif", ".jpg", ".png", ".jpeg", ".gif")
    OFFICE = (".docx", ".xlsx", ".pptx", ".pdf", ".doc", ".xlsm", ".pub", ".odt")
    TEXT = (".html", ".css", ".js", ".py", ".txt", ".csv", ".json")
    ARCHIVE = (".zip", ".tar", ".7z", ".rar")


class FileOrganizer:
    def __init__(self, to_sort_path, to_exclude_files=None):
        self.to_sort_path = to_sort_path
        self.to_exclude_files = to_exclude_files
        if self.to_exclude_files is None:
            self.to_exclude_files = []
        self.destination_folders = set()

    def map_files(self):
        default_paths = {
            FileType.VIDEO: self.to_sort_path / "Video files",
            FileType.AUDIO: self.to_sort_path / "Audio files",
            FileType.IMAGE: self.to_sort_path / "Image files",
            FileType.OFFICE: self.to_sort_path / "Office files",
            FileType.TEXT: self.to_sort_path / "Text files",
            FileType.ARCHIVE: self.to_sort_path / "Archive files",
        }
        mapped_files = defaultdict(lambda: self.to_sort_path / "Others")

        for file in self.get_files():
            for file_type, path in default_paths.items():
                if file.suffix.lower() in file_type.value:
                    mapped_files[file.suffix] = path

        return mapped_files

    def should_exclude(self, file):
        return any(to_exclude in file.parts for to_exclude in self.to_exclude_files)

    def get_files(self, folder=None):
        if folder is not None:
            files = [
                file for file in folder.glob("*")
                if file.is_file() and not self.should_exclude(file)
            ]
        else:
            files = [
                file for file in self.to_sort_path.rglob("*")
                if file.is_file() and not self.should_exclude(file)
            ]
        return files

    def get_folders(self):
        return [folder for folder in self.to_sort_path.rglob("*/")if not self.should_exclude(folder)]

    @staticmethod
    def move_file(file, dest):
        if dest.exists() and dest.is_file():
            logging.debug('Destination folder is a file using file parent as dest...')
            dest = dest.parent

        destination_file = dest / file.name
        if not destination_file.exists():
            dest.mkdir(parents=True, exist_ok=True)

        if destination_file.exists() and not destination_file.samefile(file):
            destination_file = new_filepath(destination_file, add_prefix='_Duplicate')

        if not destination_file.exists():
            logging.debug(f'Moving {file} to {dest}')
            shutil.move(file, destination_file)

    def type_sort(self):
        unsorted_files = self.get_files()
        mapped_files = self.map_files()

        for file in unsorted_files:
            type_dest = mapped_files[file.suffix]
            ext_dest = type_dest.joinpath(file.suffix.strip(".") + " files" if file.suffix else " unknown files")
            self.move_file(file, ext_dest)
            self.destination_folders.update({type_dest, ext_dest})

    def prefix_sort(self, folder):
        unsorted_files = self.get_files(folder)
        prefix_folders = defaultdict(list)

        for file in unsorted_files:
            prefix = get_split_stem(SPLIT_PATTERN, TO_REPLACE_PATTERN, file.stem)[0]
            prefix_folders[prefix].append(file)

        if len(prefix_folders) > 1:
            for prefix, files in prefix_folders.items():
                if len(files) > 1:
                    for file in files:
                        if prefix not in file.parts:
                            prefix_folder = file.parent / prefix
                            self.move_file(file, prefix_folder)
                            self.destination_folders.add(prefix_folder)

    def stem_sort(self, folder):
        unsorted_files = self.get_files(folder)
        common_stems = get_common_stems(unsorted_files)
        file_stems = [get_split_stem(SPLIT_PATTERN, TO_REPLACE_PATTERN, file.stem) for file in unsorted_files]

        stem_folders = defaultdict(list)
        for file, file_stem in zip(unsorted_files, file_stems):
            for common_stem in common_stems:
                if len(common_stem) <= len(file_stem) and all(x == y for x, y in zip(common_stem, file_stem)):
                    stem_folders[' '.join(common_stem).strip()].append(file)

        if len(stem_folders) > 1:
            #  Move files to folders with longer common stem first.
            for common_stem in reversed(sorted(stem_folders, key=len)):
                files = stem_folders[common_stem]
                if len(files) > 1:
                    for file in files:
                        if not set(common_stem.split()) <= set(file.parts):
                            stem_folder = file.parent / common_stem
                            self.destination_folders.add(stem_folder)
                            try:
                                self.move_file(file, stem_folder)
                            except FileNotFoundError:
                                pass  # A file mapped for the shortest common stem might be moved inside a folder
                                # with longer common stem.

    def run(self):
        unsorted_files = self.get_files()
        logging.info('Running type_sort...')
        self.type_sort()

        logging.info('Running prefix_sort...')
        for folder in self.get_folders():
            self.prefix_sort(folder)

        logging.info('Running stem_sort...')
        for folder in self.get_folders():
            self.stem_sort(folder)

        empty_folders = set(self.get_folders()) - self.destination_folders
        remove_folders(empty_folders)

        logging.info('Verifying files...')
        verify_files(unsorted_files, self.get_files())


def verify_files(unsorted_files, sorted_files):
    is_ok = len(unsorted_files) == len(sorted_files)
    if is_ok:
        logging.info(f"File organization successful!")
    else:
        removed_files = set(unsorted_files) - set(sorted_files)
        if removed_files:
            logging.error(f"Files are deleted: ")
            for file in removed_files:
                logging.error(f'Deleted: {file}')


def remove_folders(folders):
    if folders:
        logging.info('Moving empty folders to trash...')
        for folder in folders:
            logging.debug(f'Moving {folder} to trash...')
            send2trash(str(folder))


def split_stem(split_pattern, stem):
    return re.split(split_pattern, stem)


def clean_stem(to_replace_pattern, stem, replacement=''):
    return re.sub(to_replace_pattern, replacement, stem).strip()


def get_split_stem(split_pattern, to_replace_pattern, stem):
    return split_stem(split_pattern, clean_stem(to_replace_pattern, stem))


def get_common_stems(files):
    file_stems = [get_split_stem(SPLIT_PATTERN, TO_REPLACE_PATTERN, file.stem) for file in files]

    common_stems = []
    for x_combination, y_combination in combinations(file_stems, 2):
        common_stem = [x for x, y in zip_longest(x_combination, y_combination, fillvalue='fill in') if x == y]
        common_stems.append(tuple(common_stem))

    common_stems = list(set(common_stems))
    common_stems = [list(common_stem) for common_stem in common_stems if common_stem and len(set(common_stem)) > 1]

    return common_stems


def main():
    to_sort_path = Path('C:/Users/KENNETH/Desktop/Test Folder')
    orgnizer = FileOrganizer(to_sort_path)
    orgnizer.run()


if __name__ == "__main__":
    configure_logging(log_level=logging.INFO)
    main()
