import os
import zipfile
from pathlib import Path

from helper import get_folder_path, confirm

FOLDERS_TO_EXCLUDE = ('__pycache__', '.venv')
FILES_TO_EXCLUDE = ('default.rdp', 'desktop.ini')


def is_to_exclude(file_name):
    return file_name.lower() in FILES_TO_EXCLUDE


def create_zip(archive_file, folder_path, compress_level):
    with zipfile.ZipFile(archive_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=compress_level) as archive:
        for root, dirs, files in os.walk(folder_path):
            root = Path(root)
            if root.name not in FOLDERS_TO_EXCLUDE:
                print(f'Adding files from {root.name}')
                for file in files:
                    file_path = root / file
                    if not is_to_exclude(file_path.name):
                        arcname = file_path.relative_to(folder_path)
                        print(f'Adding {arcname.name} ...')
                        archive.write(file_path, arcname=arcname)


def update_zip(archive_file, folder_path, compress_level):
    with zipfile.ZipFile(archive_file, 'a', zipfile.ZIP_DEFLATED, compresslevel=compress_level) as archive:
        existing_contents = set(archive.namelist())
        for root, dirs, files in os.walk(folder_path):
            root = Path(root)
            if root.name not in FOLDERS_TO_EXCLUDE:
                print(f'Adding files from {root.name}')
                for file in files:
                    file_path = root / file
                    if not is_to_exclude(file_path.name):
                        arcname = file_path.relative_to(folder_path)
                        if arcname.as_posix() not in existing_contents:
                            print(f'Adding {arcname.name} ...')
                            archive.write(file_path, arcname=arcname)


def archiver(archive_file, folder_path, compress_level):
    archive_file = Path(archive_file)
    folder_path = Path(folder_path)

    try:
        if not archive_file.exists():
            print(f'Creating {archive_file.name}...')
            create_zip(archive_file, folder_path, compress_level)
            print(f"Archive created successfully!")
        else:
            print(f'Updating {archive_file.name}...')
            update_zip(archive_file, folder_path, compress_level)
            print(f"Archive updated successfully!")
    except Exception as e:
        print(f"Error updating archive: {str(e)}")


def main():
    folder_to_backup = get_folder_path('of folder you want to backup')
    backups_folder = Path('D:/KENNETH/Backups/Archives')
    compress_level = 6
    if confirm('Create a zip archive for this folder?', confirm_letter='yes'):
        archive_file = backups_folder / f'{folder_to_backup.name}.zip'
        archiver(archive_file, folder_to_backup, compress_level)


if __name__ == '__main__':
    main()



import os
import zipfile
from pathlib import Path
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


def create_archive(archive_path, folder_path, compress_level):
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compress_level) as archive:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(folder_path)
                print(f'Adding {arcname} to archive...')
                archive.write(file_path, arcname=arcname)


def update_archive(archive_path, folder_path, compress_level):
    with zipfile.ZipFile(archive_path, 'a', zipfile.ZIP_DEFLATED, compresslevel=compress_level) as archive:
        existing_contents = set(Path(name) for name in archive.namelist())

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(folder_path)

                # Check if the file is not already in the archive
                if arcname not in existing_contents:
                    print(f'Adding {arcname} to archive...')
                    archive.write(file_path, arcname=arcname)


def upload_to_google_drive(file_path, folder_name):
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LocalWebserverAuth()

    drive = GoogleDrive(gauth)

    # Find the folder in Google Drive
    folder_query = f"title = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    folder_list = drive.ListFile({'q': folder_query}).GetList()

    if not folder_list:
        # Create the folder if it doesn't exist
        folder = drive.CreateFile({'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'})
        folder.Upload()
    else:
        folder = folder_list[0]

    # Upload the file to the folder
    file_drive = drive.CreateFile({'title': file_path.name, 'parents': [{'id': folder['id']}]})
    file_drive.Upload()

    print(f"File '{file_path.name}' uploaded to Google Drive folder '{folder_name}'")


def archiver_and_upload(archive_backup, folder_path, compress_level, folder_name):
    archive_backup = Path(archive_backup)
    folder_path = Path(folder_path)

    try:
        # If the archive file doesn't exist, create a new archive
        if not archive_backup.exists():
            print(f'Creating {archive_backup.name}...')
            create_archive(archive_backup, folder_path, compress_level)
            print(f"Archive created successfully!")
        else:
            # Open the existing archive in update mode and add only new files
            print(f'Updating {archive_backup.name}...')
            update_archive(archive_backup, folder_path, compress_level)
            print(f"Archive updated successfully!")

        # Upload the file to Google Drive
        upload_to_google_drive(archive_backup, folder_name)

    except Exception as e:
        print(f"Error updating archive and uploading to Google Drive: {str(e)}")


# Example usage
folder_to_backup = Path('~/Desktop/Documents').expanduser()
archive_backup_path = Path('D:/Backups/Archives') / f'{folder_to_backup.name}_backup.zip'
compress_level = 6
google_drive_folder_name = 'YourGoogleDriveFolderName'  # Replace with your desired Google Drive folder name

archiver_and_upload(archive_backup_path, folder_to_backup, compress_level, google_drive_folder_name)


if __name__ == '__main__':
    pass
