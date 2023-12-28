import re
import sys
from pathlib import Path
import pyperclip


def clean_file(file, to_remove):
    org_file = Path(file).absolute()
    tmp_file = org_file.with_suffix(".tmp")

    with open(org_file, "r") as in_file, open(tmp_file, "w") as out_file:
        for line in in_file.readlines():
            for word in to_remove:
                line = re.sub(word, "", line)
            out_file.write(line)

    tmp_file.replace(org_file)


def main():
    args = sys.argv

    if len(args) > 1:
        _, file, *words_to_remove = args

    else:
        file = pyperclip.paste()
        if not file:
            raise ValueError("Clipboard is empty!")
        print("Enter the words you to remove from file separated by spaces:")
        words_to_remove = input("> ").split()

    file = Path(file)

    if file.is_dir():
        print("Enter the extension for files:")
        ext = input("> ")

        for d_file in file.glob(f"*{ext}"):
            print("Removing unwanted words from: " + d_file.name)
            clean_file(d_file, words_to_remove)

    else:
        clean_file(file, words_to_remove)

    print("Done!")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(str(e))
    except FileNotFoundError as e:
        print(str(e))
