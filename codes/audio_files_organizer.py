import os
import shutil
import logging
from pathlib import Path
from collections import defaultdict

import acoustid
from mutagen.easyid3 import EasyID3
from send2trash import send2trash

from helper import configure_logging, get_folder_path

fpcalc_path = 'C:/coding/python/tools/chromaprint-fpcalc-1.5.1-windows-x86_64'
os.environ['PATH'] = f"{os.environ['PATH']};{fpcalc_path}"

AUDIO_FILES = ('.mp3', '.wav', '.flac', '.m4a')


def is_audio(file):
    return file.is_file() and file.suffix.lower() in AUDIO_FILES


def generate_fingerprint(audio_file):
    duration, fingerprint = acoustid.fingerprint_file(audio_file)
    return fingerprint


def get_metadata(audio_file):
    audio = EasyID3(audio_file)
    return {
        'artist': audio.get('artist', ['Unknown'])[0],
        'album': audio.get('album', ['Unknown'])[0],
        'title': audio.get('title', ['Unknown'])[0]
    }


def get_duplicates(mapped_fingerprints):
    logging.info('getting duplicates...')
    duplicates = []
    for files in mapped_fingerprints.values():
        if len(files) > 1:
            for file in files[1:]:
                duplicates.append(file)

    return duplicates


def map_fingerprints(audio_files):
    logging.info('mapping audio fingerprints...')

    mapped_fingerprints = defaultdict(list)
    for file in audio_files:
        logging.debug(f'Current file: {file.name}')
        try:
            mapped_fingerprints[generate_fingerprint(file)].append(file)
        except acoustid.FingerprintGenerationError:
            logging.error(f'Error generating audio fingerprint for: {file.name}')

    return mapped_fingerprints


def handle_duplicates(duplicates, directory):
    duplicates_dest = Path(directory).absolute() / 'duplicates'
    duplicates_dest.mkdir(exist_ok=True)

    logging.info('Moving duplicates...')
    for duplicate in duplicates:
        logging.debug(f'moving {duplicate.name} to duplicates folder...')
        shutil.move(duplicate, duplicates_dest)

    logging.info('moving duplicates folder to trash...')
    send2trash(duplicates_dest)


def organize_music_files(directory):
    configure_logging(log_level=logging.INFO)
    audio_files = {file for file in Path(directory).glob('*') if is_audio(file)}
    duplicates = get_duplicates(map_fingerprints(audio_files))
    if duplicates:
        handle_duplicates(duplicates, directory)
    else:
        logging.info('No duplicate found.')


if __name__ == '__main__':
    music_directory = get_folder_path('music folder to remove duplicates.')
    organize_music_files(music_directory)
