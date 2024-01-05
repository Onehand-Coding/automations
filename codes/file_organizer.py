import re
import shutil
from enum import Enum
from itertools import combinations
from collections import defaultdict

from send2trash import send2trash

from helper import get_folder_path, new_filepath, confirm

TO_REPLACE_PATTERN = re.compile(r'\[.*\]|\(.*\)')
SPLIT_PATTERN = re.compile(r'\s+|[.,:_-]')


class FileType(Enum):
    VIDEO = (".mp4", ".mkv", ".webm", ".3gp")
    AUDIO = (".mp3", ".m4a", ".wav", ".MP3")
    IMAGE = (".jfif", ".jpg", ".png", ".jpeg", ".JPG", ".gif")
    OFFICE = (".docx", ".xlsx", ".pptx", ".pdf", ".doc", ".xlsm", ".pub", ".odt")
    TEXT = (".html", ".css", ".js", ".py", ".txt", ".csv", ".json")
    ARCHIVE = (".zip", ".tar", ".7z", ".rar")


def map_files(files, to_sort_path):
    default_paths = {
        FileType.VIDEO: to_sort_path / "Video files",
        FileType.AUDIO: to_sort_path / "Audio files",
        FileType.IMAGE: to_sort_path / "Image files",
        FileType.OFFICE: to_sort_path / "Office files",
        FileType.TEXT: to_sort_path / "Text files",
        FileType.ARCHIVE: to_sort_path / "Archive files",
    }
    mapped_files = defaultdict(lambda: to_sort_path / "Others")

    for file in files:
        for file_type, path in default_paths.items():
            if file.suffix in file_type.value:
                mapped_files[file.suffix] = path

    return mapped_files


def move_file(file, dest):
    if file.exists():
        if not dest.exists():
            dest.mkdir(parents=True, exist_ok=True)

        destination_file = dest / file.name
        if destination_file.exists() and not file.samefile(destination_file):
            destination_file = new_filepath(destination_file, add_prefix='_Duplicate')
        try:
            shutil.move(file, destination_file)
        except FileNotFoundError:
            pass


def verify_files(unsorted_files, sorted_files, method='Agressive'):
    is_ok = len(sorted_files) == len(unsorted_files)
    if is_ok:
        print(f"{method} sort successful!")
    else:
        removed_files = set(unsorted_files) - sorted_files
        if removed_files:
            print(f"Some files are Removed!")
            for file in removed_files:
                print(file.name)


def remove_folders(folders):
    for folder in folders:
        send2trash(str(folder))


def should_exclude(file, to_exclude_files):
    return any(to_exclude in file.parts for to_exclude in to_exclude_files)


def split_stem(split_pattern, stem):
    return re.split(split_pattern, stem)


def clean_stem(to_replace_pattern, stem, replacement=''):
    return re.sub(to_replace_pattern, replacement, stem).strip()


def get_all_folders(to_sort_path, to_exclude_files):
    return {
        folder for folder in to_sort_path.rglob("*/")
        if not should_exclude(folder, to_exclude_files)
    }


def get_all_files(to_sort_path, to_exclude_files):
    return {
        file for file in to_sort_path.rglob("*")
        if file.is_file() and not should_exclude(file, to_exclude_files)
    }


def get_common_prefixes(files):
    split_file_stems = [split_stem(SPLIT_PATTERN, clean_stem(TO_REPLACE_PATTERN, file.stem)) for file in files]

    common_prefixes = []
    for x_combination, y_combination in combinations(split_file_stems, 2):
        common_prefix = []
        for i in range(len(x_combination)):
            first_word = x_combination[0]
            try:
                if x_combination[i] == y_combination[i]:
                    common_prefix.append(x_combination[i])
            except IndexError:
                pass
        try:
            common_prefix = common_prefix[:common_prefix.index(first_word, 1)]
        except (ValueError, IndexError):
            pass
        common_prefixes.append(tuple(common_prefix))

    common_prefixes = list(set(common_prefixes))
    common_prefixes = [
        list(common_prefix)
        for common_prefix in common_prefixes
        if common_prefix and len(set(prefix.lower() for prefix in common_prefix)) > 1
    ]
    return common_prefixes


def stem_sort(to_sort_path):
    unsorted_files = [file for file in to_sort_path.glob("*") if file.is_file()]
    common_prefixes = get_common_prefixes(unsorted_files)

    prefix_folders = defaultdict(list)
    for file in unsorted_files:
        split_file_stem = split_stem(SPLIT_PATTERN, clean_stem(TO_REPLACE_PATTERN, file.stem))
        for common_prefix in common_prefixes:
            try:
                if (all(common_prefix[i] == split_file_stem[i] for i in range(len(common_prefix)))):
                    prefix_folders[' '.join(common_prefix)].append(file)
            except IndexError:
                pass

    if len(prefix_folders.keys()) > 1:
        for prefix, files in prefix_folders.items():
            if len(files) > 1:
                for file in files:
                    if prefix not in file.parts:
                        stem_folder = file.parent / prefix
                        move_file(file, stem_folder)


def prefix_sort(to_sort_path):
    unsorted_files = [file for file in to_sort_path.glob("*") if file.is_file()]
    prefix_folders = defaultdict(list)

    for file in unsorted_files:
        prefix = split_stem(SPLIT_PATTERN, clean_stem(TO_REPLACE_PATTERN, file.stem))[0]
        prefix_folders[prefix].append(file)

    if len(prefix_folders.keys()) > 1:
        for prefix, files in prefix_folders.items():
            if len(files) > 1:
                for file in files:
                    if prefix not in file.parts:
                        prefix_folder = file.parent / prefix
                        move_file(file, prefix_folder)


def simple_sort(to_sort_path):
    unsorted_files = {file for file in to_sort_path.glob("*") if file.is_file()}
    existing_folders = set(to_sort_path.glob('*/'))

    for file in unsorted_files:
        ext_dest = file.parent.joinpath(file.suffix.strip(".") + " files" if file.suffix else " unknown files")
        move_file(file, ext_dest)

    new_folders = set(to_sort_path.glob('*/')) - existing_folders
    for folder in new_folders:
        prefix_sort(folder)

    print("Simple sort Done!")


def agressive_sort(to_sort_path, to_exclude_files=None):
    if to_exclude_files is None:
        to_exclude_files = []
    unsorted_files = get_all_files(to_sort_path, to_exclude_files)
    mapped_files = map_files(unsorted_files, to_sort_path)
    default_folders = set()

    for file in unsorted_files:
        type_dest = mapped_files[file.suffix]
        ext_dest = type_dest.joinpath(file.suffix.strip(".") + " files" if file.suffix else " unknown files")
        move_file(file, ext_dest)
        default_folders.update({type_dest, ext_dest})

    all_folders = get_all_folders(to_sort_path, to_exclude_files)
    empty_folders = all_folders - default_folders
    remove_folders(empty_folders)

    for folder in all_folders:
        prefix_sort(folder)

    for i in range(2):
        for folder in get_all_folders(to_sort_path, to_exclude_files):
            stem_sort(folder)

    sorted_files = get_all_files(to_sort_path, to_exclude_files)
    verify_files(unsorted_files, sorted_files)


def main():
    to_sort_dir = get_folder_path(task="folder you want to organize files from")

    if confirm("Simple sort?", confirm_letter="yes"):
        print(f'Organizing files in {to_sort_dir.name} ...')
        simple_sort(to_sort_dir)
    elif confirm("Aggressive sort?", confirm_letter="yes"):
        print(f'Organizing files in {to_sort_dir.name} ...')
        agressive_sort(to_sort_dir)


if __name__ == "__main__":
    main()
