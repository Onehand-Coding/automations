# Script to move specific file types from a folder to another.
import sys
import shutil

from helper import confirm, get_folder_path


def get_file_type():
    print("Enter file type you want to move. eg., .txt")
    return input("> ").strip()


def get_files_to_move(source, destination, filetype):
    files_to_move = list(source.glob(f'*{filetype}'))

    if not files_to_move:
        raise FileNotFoundError(f"No '{filetype}' files found in {source}")
    if source.samefile(destination):
        raise shutil.SameFileError(f"Same source and destination.")

    return files_to_move


def overwrite_all(files, dest):
    for file in files:
        print(f"moving {file.name}...")
        # move files forcibly
        file.replace(dest / file.name)


def skip_all(files, dest):
    for file in files:
        print(f"moving {file.name}...")
        shutil.move(file, dest)


def move_files(files_to_move, destination, filetype):
    moved_files = 0

    for current_file in files_to_move:
        try:
            print(f"moving {current_file.name} ...")
            shutil.move(current_file, destination)
            moved_files += 1
        except shutil.Error:
            duplicated = files_to_move[files_to_move.index(current_file):]
            duplicates = [file for file in duplicated if (destination / file.name).exists()]
            no_duplicates = [file for file in duplicated if not (destination / file.name).exists()]

            if confirm(f"{current_file.name} already exists in destination, Overwrite?"):
                print(f"The destination has {len(duplicates)} '{filetype}' files with the same name!")
                if confirm("Overwrite all?"):
                    overwrite_all(duplicated, destination)
                    moved_files = len(files_to_move)
                    break
                print(f"{current_file.name} moved")
                current_file.replace(destination / current_file.name)
                moved_files += 1

            if confirm("Skip all?"):
                skip_all(no_duplicates, destination)
                moved_files += len(no_duplicates)
                break
            duplicated.remove(current_file)

    print("\n", moved_files, "files" if moved_files > 1 else "file", "moved!")


def main():
    source = get_folder_path('folder you want to move files from')
    filetype = get_file_type()
    destination = get_folder_path(f'folder you want to move {filetype} files to')

    try:
        move_files(get_files_to_move(source, destination, filetype), destination, filetype)
    except (FileNotFoundError, shutil.SameFileError) as e:
        print(f"\nError! {str(e)}")
    except Exception:
        raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('Bye!')
        sys.exit()
