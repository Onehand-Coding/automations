import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Union, Optional, Callable


def confirm(question: str, /, *, choice: str = "[Y/N] :", confirm_letter: str = 'y') -> bool:
    """Prompt user for confirmation.

    Args:
        question: Question to ask the user
        choice: Choices to display to the user
        confirm_letter: Letter that confirms the action

    Returns:
        True if user confirmed, False otherwise
    """
    return input(f"{question} {choice} ").lower().strip().startswith(confirm_letter)


def get_str_datetime(date_format: str = '%B %d, %Y  %I:%M %p') -> str:
    """Get the current date and time as a formatted string.

    Args:
        date_format: Format string for the datetime

    Returns:
        Formatted datetime string
    """
    return datetime.now().strftime(date_format)


def get_valid_num() -> int:
    """Get valid integer input from user.

    Returns:
        Valid integer input
    """
    while True:
        try:
            return int(input('> '))
        except ValueError:
            print('Enter an integer!')


def get_index(list_of_data: List) -> int:
    """Get a valid index from the user.

    Args:
        list_of_data: List for which to get a valid index

    Returns:
        Zero-based index chosen by the user
    """
    length = len(list_of_data)
    while True:
        index = get_valid_num()
        if 1 <= index <= length:
            return index - 1
        print(f"Index should be between 1 and {length}. Try again.")


def new_filepath(file: Union[str, Path], *, parent: Optional[Union[str, Path]] = None,
                add_prefix: str = '', start_count: int = 1) -> Path:
    """Generate a new filepath to avoid duplicates.

    Args:
        file: Original file path
        parent: Parent directory for the new file
        add_prefix: Prefix to add before the counter
        start_count: Initial counter value

    Returns:
        Path object with unique filename
    """
    file_path = Path(file)
    base_path = Path(parent).absolute() / file_path if parent else file_path

    while True:
        new_path = base_path.parent / f'{base_path.stem}{add_prefix}({start_count}){base_path.suffix}'
        if not new_path.exists():
            return new_path
        start_count += 1


def get_folder_path(task: str) -> Path:
    """Prompt the user to enter a valid folder path.

    Args:
        task: Description of the folder's purpose

    Returns:
        Path object representing the validated folder path
    """
    print(f'Enter the absolute path for {task}')
    while True:
        path = input('> ').strip()
        if path and Path(path).exists():
            return Path(path).absolute()
        print('Invalid path. Please enter a valid path!')


def choose(choices: List, task: str = '') -> Any:
    """Prompt the user to choose an item from a list.

    Args:
        choices: List of items to choose from
        task: Description of what is being chosen

    Returns:
        The chosen item
    """
    if not isinstance(choices, list) or len(choices) <= 1:
        raise ValueError('Choices must be a list with more than one element.')

    if len(choices) == 2:
        print(*choices, sep=' or ', end='?\n')
        choice = None
        while choice not in choices:
            choice = input('> ')
        return choice

    article = 'an' if task and task[0].lower() in 'aeiou' else 'a'
    print(f'Choose {article} {task}')
    for index, item in enumerate(choices, start=1):
        print(index, item)
    return choices[get_index(choices)]


def write_to_json(json_file: Union[str, Path], json_key: str, json_data: Any, indent: int = 4) -> None:
    """Write data to a JSON file with specified key.

    Args:
        json_file: Path to the JSON file
        json_key: Key for the data in the JSON file
        json_data: Data to write
        indent: Indentation level for JSON formatting
    """
    with open(json_file, "w") as f:
        json.dump({json_key: json_data}, f, indent=indent)


def read_print_json(json_file: Union[str, Path]) -> None:
    """Read and print contents of a JSON file with formatting.

    Args:
        json_file: Path to the JSON file
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    print(json.dumps(data, indent=4))


def csv_dict_writer(filename: Union[str, Path], data: List[Dict], *,
                   delimiter: str = ",", fieldnames: Optional[List[str]] = None) -> None:
    """Write list of dictionaries to a CSV file.

    Args:
        filename: Path to the CSV file
        data: List of dictionaries to write
        delimiter: Delimiter character for CSV
        fieldnames: List of field names for CSV header
    """
    if fieldnames is None:
        raise TypeError("Missing required keyword argument fieldnames.")

    with open(filename, "w", newline="") as f:
        csv_writer = csv.DictWriter(f, delimiter=delimiter, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(data)


def read_csv_dict_output(csv_file: Union[str, Path], *, delimiter: str = ',') -> None:
    """Read and print contents of a CSV file as dictionaries.

    Args:
        csv_file: Path to the CSV file
        delimiter: Delimiter character for CSV
    """
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f, delimiter=delimiter)
        for row in csv_reader:
            for key, value in row.items():
                print(f'{key}: {value}')
            print()


def read_csv_list_output(csv_file: Union[str, Path], *, delimiter: str = ',') -> None:
    """Read and print contents of a CSV file as lists.

    Args:
        csv_file: Path to the CSV file
        delimiter: Delimiter character for CSV
    """
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.reader(f, delimiter=delimiter)
        headers = next(csv_reader)
        print()
        print(*headers)
        print()
        for row in csv_reader:
            print(*row)
