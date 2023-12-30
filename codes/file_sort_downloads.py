from pathlib import Path
from file_organizer import agressive_sort, simple_sort
from helper import choose

DOWNLOADS = Path('~/Downloads').expanduser()


def main():
    print('Sort Downloads')
    sort_methods = {
        'simple': simple_sort,
        'agressive': agressive_sort,
    }
    sort_methods[choose(list(sort_methods.keys()))](DOWNLOADS)


if __name__ == '__main__':
    main()
