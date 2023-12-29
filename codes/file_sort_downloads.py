from pathlib import Path
from file_organizer import agressive_sort, simple_sort

DOWNLOADS = Path('~/Downloads').expanduser()


def main():
    print('Sort Downloads')
    sort_methods = {
        'simple': simple_sort,
        'agressive': agressive_sort,
    }
    print(*list(sort_methods.keys()), sep=' or ', end='?\n')
    sort_method = None
    while sort_method not in sort_methods:
        sort_method = input('> ').strip().lower()
    sort_methods.get(sort_method)(DOWNLOADS)


if __name__ == '__main__':
    main()
