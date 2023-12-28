# Removes line numbering in a copy pasted python source code.
import re
import sys
from pathlib import Path
import pyperclip

numberingPattern = r'\d+\.'


def removeNumbering(file):
    with open(file, 'r', encoding='utf-8') as fp:
        new_lines = []

        for line in fp:
            line = re.sub(numberingPattern, '', line).lstrip(' ')
            new_lines.append(line)

    return new_lines


def isNumbered(file):
    with open(file, "r", encoding='utf-8') as inputFile:
        return any(re.match(numberingPattern, line) for line in inputFile)


def writeData(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        f.writelines(data)


def getFile(args):
    if len(args) > 1:
        file = args[1]
    else:
        file = pyperclip.paste()
        if not file:
            raise FileNotFoundError(f'clipboard is empty!')

    file = Path(file)

    if not file.exists():
        raise FileNotFoundError(f'{file} not Found!')
    elif file.is_dir():
        raise IsADirectoryError(f'{file} is a Directory, not File!')
    elif not isNumbered(file):
        raise TypeError(f'{file} content is not Numbered!')
    return file


def main():
    try:
        file = getFile(sys.argv)
        cleaned = removeNumbering(file)
    except (IsADirectoryError, FileNotFoundError, TypeError) as e:
        print(f'Failed, {e}')
    except Exception:
        raise
    else:
        writeData(file, cleaned)
        print(f'Removed numbering from {file}!')


if __name__ == '__main__':
    main()
