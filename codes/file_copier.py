# script to copy specific file types from a folder to another.
import sys
import shutil

from helper import confirm, get_folder_path


def get_file_type():
    print('Enter file type you want to copy, eg., .txt')
    return input('> ').strip()


def copy_all(files, destination):
    for file in files:
        print(f'copying {file.name}...')
        shutil.copy2(file, destination)


def get_files_to_copy(source, destination, filetype):
    files_to_copy = list(source.glob(f'*{filetype}'))

    if not files_to_copy:
        raise FileNotFoundError(f"No '{filetype}' files found in {source}")
    if source.samefile(destination):
        raise shutil.SameFileError(f"Same source and destination.")

    return files_to_copy


def copy_files(source, destination, filetype):
    files = get_files_to_copy(source, destination, filetype)

    for file in files:
        target_file = destination / file.name  # Enables us to check if the file already exists in the destination.

        if target_file.exists():
            d_index = files.index(file)
            duplicates = files[d_index:]
            if not confirm(f'{file.name} already exists in destination, Overwrite?'):
                duplicates.remove(file)  # Skipped files will not be overwritten.
                continue
            if not confirm('Overwrite all?'):
                pass
            else:
                copy_all(duplicates, destination)
                break

        print(f'copying {file.name}...')
        shutil.copy2(file, destination)
    print('Done!')


def main():
    source = get_folder_path('of folder you want to copy files from')
    filetype = get_file_type()
    destination = get_folder_path(f'of folder you want to copy {filetype} files to')

    try:
        copy_files(source, destination, filetype)
    except (FileNotFoundError, shutil.SameFileError) as e:
        print(f'\nError! {str(e)}')
    except Exception:
        raise


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Bye!')
        sys.exit()
