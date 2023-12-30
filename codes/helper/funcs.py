# Helper functions for my scripts
from datetime import datetime
from pathlib import Path


def confirm(question, /, *, choice="(Y/n)", confirm_letter='y'):
    return input(f"{question} {choice} ").lower().strip().startswith(confirm_letter)


def get_str_datetime(template='%B %d, %Y  %I:%M %p'):
    return datetime.now().strftime(template)


def get_index(list_of_data):
    length = len(list_of_data)
    while True:
        try:
            index = int(input("> ").strip())
            if 1 <= index <= length:
                return index - 1

        except ValueError:
            continue


def new_filepath(file, *, parent=None, add_prefix='', start_count=1):
    base_path = Path(parent).absolute() / file if parent else file
    new_path = base_path.parent / f'{base_path.stem}{add_prefix}({start_count}){base_path.suffix}'

    while new_path.exists():
        start_count += 1
        new_path = base_path.parent / f'{base_path.stem}{add_prefix}({start_count}){base_path.suffix}'

    return new_path


def get_folder_path(task):
    print(f'Enter the absolute path {task}')
    while True:
        path = input('> ')
        if not path or not Path(path).exists():
            print('Enter a valid path!')
            continue
        return Path(path).absolute()


def choose(choices):
    if not isinstance(choices, list):
        raise ValueError(f'Can only use {list().__class__.__name__} as choices container!')
    if not choices or len(choices) <= 1:
        raise ValueError('Argument choices must be more than one!')

    if len(choices) == 2:
        print(*choices, sep=' or ', end='?\n')
        choice = None
        while choice not in choices:
            choice = input('> ')
        return choices[choices.index(choice)]
    else:
        print('Choose item index.')
        for index, item in enumerate(choices, start=1):
            print(index, item)
        return choices[get_index(choices)]
