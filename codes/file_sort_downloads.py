from pathlib import Path
from file_organizer import agressive_sort, simple_sort
from helper import choose

DOWNLOADS = Path('~/Downloads').expanduser()
TO_EXCLUDE = ['Torrent Downloads']


def main():
    print('Sort Downloads')
    sort_methods = {
        'simple': lambda: simple_sort(DOWNLOADS),
        'agressive': lambda: agressive_sort(DOWNLOADS, TO_EXCLUDE),
    }
    choices = list(sort_methods.keys())
    function = sort_methods[choose(choices)]
    function()


if __name__ == '__main__':
    main()
