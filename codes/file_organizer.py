import re
import shutil
import stat
from enum import Enum
from collections import defaultdict

from helper import get_folder_path, new_filepath, confirm


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
    if not dest.exists():
        dest.mkdir(parents=True, exist_ok=True)

    destination_file = dest / file.name
    if destination_file.exists() and not file.samefile(destination_file):
        destination_file = new_filepath(destination_file, add_prefix='_Duplicate')

    shutil.move(file, destination_file)


def prefix_sort(to_sort_path):
    unsorted_files = {file for file in to_sort_path.glob("*") if file.is_file()}
    prefix_folders = defaultdict(list)

    for file in unsorted_files:
        prefix = re.split(r"\s+|[._-]", file.stem)[0]
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


def verify_removed(old_files, new_files, file_type):
    removed_files = set(old_files) - new_files
    if removed_files:
        print(f"Some {file_type} are Removed!")
        for file in removed_files:
            print(file.name, end=', ')


def remove_folders(folders):
    def remove_readonly(func, path, _):
        """Clear the readonly bit and reattempt the removal"""
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
        func(path)

    for folder in folders:
        try:
            shutil.rmtree(folder)
        except FileNotFoundError:
            pass
        except PermissionError:
            if confirm(f"Forcing deletion of this folder: {folder}", confirm_letter="yes"):
                shutil.rmtree(folder, onerror=remove_readonly)


def agressive_sort(to_sort_path):
    unsorted_files = {file for file in to_sort_path.rglob("*") if file.is_file()}
    mapped_files = map_files(unsorted_files, to_sort_path)
    default_folders = set()

    for file in unsorted_files:
        type_dest = mapped_files[file.suffix]
        ext_dest = type_dest.joinpath(file.suffix.strip(".") + " files" if file.suffix else " unknown files")
        move_file(file, ext_dest)
        default_folders.update({type_dest, ext_dest})

    all_folders = {file for file in to_sort_path.rglob("*/")}
    empty_folders = all_folders - default_folders
    remove_folders(empty_folders)

    for folder in all_folders:
        prefix_sort(folder)

    sorted_files = {file for file in to_sort_path.rglob("*") if file.is_file()}
    is_ok = len(sorted_files) == len(unsorted_files)

    print("Agressive sort successfully Done!" if is_ok else verify_removed(unsorted_files, sorted_files, 'files'))


def main():
    to_sort_dir = get_folder_path(task="folder you want to organize files from")

    if confirm("Simple sort?", confirm_letter="yes"):
        simple_sort(to_sort_dir)
    elif confirm("Aggressive sort?", confirm_letter="yes"):
        agressive_sort(to_sort_dir)


if __name__ == "__main__":
    main()
