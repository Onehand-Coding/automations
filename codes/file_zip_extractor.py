import zipfile

from helper import get_folder_path


def get_password():
    return input('Enter archive password: ').strip()


def extract_archive(archive_path, extract_path, password=None):
    try:
        with zipfile.ZipFile(archive_path, 'r') as archive:
            try:
                archive.extractall(extract_path)
                print(f"Archive extracted successfully to: {extract_path}")
            except zipfile.BadZipFile:
                if password:
                    archive.extractall(extract_path, pwd=password.encode('utf-8'))
                    print(f"Archive extracted successfully with password to: {extract_path}")
                else:
                    print("Error: The archive is password-protected, but no password provided.")
                    archive.extractall(extract_path, pwd=get_password().encode('utf-8'))
                    print(f"Archive extracted successfully with password to: {extract_path}")
    except Exception as e:
        print(f"Error extracting archive: {str(e)}")


def main():
    archive_file_path = get_folder_path('of archive you want to extract')
    extract_to_path = get_folder_path('of folder you want to the extract archive to')
    archive_password = None

    extract_archive(archive_file_path, extract_to_path, password=archive_password)


if __name__ == '__main__':
    main()
