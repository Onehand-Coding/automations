import json
from pathlib import Path

scriptsDataFolder = Path("~/.my scripts data").expanduser()


def readJson(jsonFile):
    with open(jsonFile, 'r') as f:
        data = json.load(f)
    print(json.dumps(data, indent=4))


def main():
    for file in scriptsDataFolder.glob('*.json'):
        if file.name.startswith('wifi'):
            print(f'Content of {file.name}:\n')
            readJson(file)


if __name__ == '__main__':
    main()
