import os
import logging
import zipfile
from pathlib import Path
from helper import get_folder_path

LOGS_DIR = Path(__file__).parents[1] / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOGS_DIR / 'file_archiver_logs.txt'), logging.StreamHandler()],
)


class ZipArchiver:
    def __init__(self, src_path, dest_path, compress_level=6, to_exclude=None):
        if to_exclude is None:
            to_exclude = []
        self.src_path = src_path
        self.archive_file = dest_path / f'{self.src_path.name}.zip'
        self.compress_level = compress_level
        self.to_exclude = to_exclude
        self.existing_contents = self.get_existing_contents()

    def should_exclude(self, file):
        return any(name in file.parts for name in self.to_exclude)

    def get_existing_contents(self):
        if not self.archive_file.exists():
            return set()
        with zipfile.ZipFile(self.archive_file, 'r') as existing_archive:
            return set(existing_archive.namelist())

    def add_files(self, archive):
        for root, dirs, files in os.walk(self.src_path):
            root = Path(root)
            if self.should_exclude(root):
                continue
            for file in files:
                file_path = root / file
                arcname = file_path.relative_to(self.src_path)
                if not self.should_exclude(arcname) and arcname.as_posix() not in self.existing_contents:
                    archive.write(file_path, arcname=arcname)

    def create(self):
        with zipfile.ZipFile(
            self.archive_file, 'w',
            zipfile.ZIP_DEFLATED,
            compresslevel=self.compress_level,
        ) as archive:

            self.add_files(archive)

    def update(self):
        with zipfile.ZipFile(
            self.archive_file, 'a',
            zipfile.ZIP_DEFLATED,
            compresslevel=self.compress_level,
        ) as archive:

            self.add_files(archive)

    def run(self):
        try:
            if not self.archive_file.exists():
                logging.info(f'Creating {self.archive_file.name}...')
                self.create()
                logging.info(f"Archive created successfully!")
            else:
                logging.info(f'Updating {self.archive_file.name}...')
                self.update()
                logging.info(f"Archive updated successfully!")

        except (zipfile.BadZipFile, PermissionError) as e:
            logging.error(f"Error updating archive: {str(e)}")
        except Exception as e:
            logging.error(f'Error: {str(e)}')
        except KeyboardInterrupt:
            logging.error('Script interrupted!')


def main():
    folder_to_archive = get_folder_path('folder you want to archive')
    backups_folder = Path('D:/KENNETH/Backups')
    compress_level = 6
    to_exclude = ['__pycache__', '.venv', 'default.rdp', 'desktop.ini']

    zip_archiver = ZipArchiver(folder_to_archive, backups_folder, compress_level, to_exclude)
    zip_archiver.run()


if __name__ == '__main__':
    main()
