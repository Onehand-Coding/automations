from pathlib import Path
from helper import read_print_json

scriptsDataFolder = Path("~/.my scripts data").expanduser()


def main():
    for file in scriptsDataFolder.glob('*.json'):
        if file.name.startswith('wifi'):
            print(f'Content of {file.name}:\n')
            read_print_json(file)


if __name__ == '__main__':
    main()
