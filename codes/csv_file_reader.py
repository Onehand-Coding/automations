from pathlib import Path
import csv


def dict_output(csv_file):
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f, delimiter=',')
        for data in csv_reader:
            for key in data:
                print(f'{key}: {data.get(key)}')
            print()


def list_output(csv_file):
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.reader(f, delimiter=',')
        headers = next(csv_reader)
        print()
        print(*headers)
        print()
        for data in csv_reader:
            print(*data)


def main():
    scripts_data_folder = Path("~/.my scripts data").expanduser()
    csv_files = scripts_data_folder.glob('*.csv')

    for file in csv_files:
        print(f'\n{file.name}\n')
        if input('output as dictionary? (Y/n) ').lower().startswith('y'):
            print(f'Content of: {file.name}\n')
            dict_output(file)
            input('Press Enter...')
            continue
        list_output(file)


if __name__ == '__main__':
    main()
