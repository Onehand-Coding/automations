from pathlib import Path
from file_organizer import FileOrganizer
from helper import choose, configure_logging

DOWNLOADS = Path('~/Downloads').expanduser()
TO_EXCLUDE = ['Torrent Downloads']


def main():
    print('Sort Downloads')
    organizer = FileOrganizer(DOWNLOADS, TO_EXCLUDE)
    sort_methods = {
        'simple': lambda: organizer.simple_sort(),
        'agressive': lambda: organizer.agressive_sort(),
    }
    choices = list(sort_methods.keys())
    method = sort_methods[choose(choices)]
    method()


if __name__ == '__main__':
    configure_logging()
    main()
