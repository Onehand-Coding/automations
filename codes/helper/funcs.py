# Helper functions for my scripts
import json
import csv
from pathlib import Path
from datetime import datetime


def confirm(question, /, *, choice="(Y/n)", confirm_letter='y'):
    """Prompt user for confirmation."""
    return input(f"{question} {choice} ").lower().strip().startswith(confirm_letter)


def get_str_datetime(date_format='%B %d, %Y  %I:%M %p'):
    """Get the current date and time as a formatted string."""
    return datetime.now().strftime(date_format)


def get_valid_num():
    """Get valid integer input from user."""
    valid_num = ''
    while not valid_num:
        try:
            valid_num = int(input('> '))
        except ValueError:
            print('Enter an integer!')

    return valid_num


def get_index(list_of_data):
    """Get a valid index from the user."""
    length = len(list_of_data)
    while True:
        index = get_valid_num()
        if 1 <= index <= length:
            return index - 1
        else:
            print(f"Index should be between 1 and {length}. Try again.")


def new_filepath(file, *, parent=None, add_prefix='', start_count=1):
    """Generate a new filepath to avoid duplicates."""
    base_path = Path(parent).absolute() / file if parent else file
    new_path = base_path.parent / f'{base_path.stem}{add_prefix}({start_count}){base_path.suffix}'

    while new_path.exists():
        start_count += 1
        new_path = base_path.parent / f'{base_path.stem}{add_prefix}({start_count}){base_path.suffix}'

    return new_path


def get_folder_path(task):
    """Prompt the user to enter a valid folder path."""
    print(f'Enter the absolute path for {task}')
    while True:
        path = input('> ')
        if not path or not Path(path).exists():
            print('Invalid path. Please enter a valid path!')
        else:
            return Path(path).absolute()


def choose(choices, task=''):
    """Prompt the user to choose an item from a list."""
    if not isinstance(choices, list) or len(choices) <= 1:
        raise ValueError('Choices must be a list with more than one element.')

    if len(choices) == 2:
        print(*choices, sep=' or ', end='?\n')
        choice = None
        while choice not in choices:
            choice = input('> ')
        return choices[choices.index(choice)]
    else:
        letter = 'an' if task[0] in 'aeiou' else 'a'
        print(f'Choose {letter} {task}')
        for index, item in enumerate(choices, start=1):
            print(index, item)
        return choices[get_index(choices)]


def write_to_json(json_file, json_key, json_data, indent=4):
    with open(json_file, "w") as f:
        json.dump({json_key: json_data}, f, indent=indent)


def read_print_json(jsonFile):
    with open(jsonFile, 'r') as f:
        data = json.load(f)
    print(json.dumps(data, indent=4))


def csv_dict_writer(filename, data, *, delimiter=",", fieldnames=None):
    if fieldnames is None:
        raise TypeError("Missing required keyword argument fieldnames.")

    with open(filename, "w", newline="") as f:
        csv_writer = csv.DictWriter(f, delimiter=delimiter, fieldnames=fieldnames)

        csv_writer.writeheader()
        for csv_data in data:
            csv_writer.writerow(csv_data)


def read_csv_dict_output(csv_file, *, delimiter=','):
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f, delimiter=delimiter)
        for data in csv_reader:
            for key in data:
                print(f'{key}: {data.get(key)}')
            print()


def read_csv_list_output(csv_file, *, delimiter=','):
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.reader(f, delimiter=delimiter)
        headers = next(csv_reader)
        print()
        print(*headers)
        print()
        for data in csv_reader:
            print(*data)
