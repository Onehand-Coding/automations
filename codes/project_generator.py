import os
import json
import subprocess
from pathlib import Path

MAIN_PROJECT_FOLDER = Path('C:/coding/python/my_codes/projects')

project_sub_folders = ['.sublime-project-files', 'codes', 'resources', 'logs', 'data']
project_files = ['README.md', 'requirements.txt']
ignored_files = [
    '#===== Default ignored =====#\n',
    '# Folders #\n',
    '.sublime-project-files/\n',
    '__pycache__/\n',
    '.venv/\n',
    'resources/\n',
    'data/\n',
    'logs/\n',
    '# Files #\n',
    '__main__.py\n',
    '__init__.py\n',
    'scratch.py\n',
    '#===== Project ignored =====#\n',
    '# Folders #\n',
    'tests/\n',
    '# Files #\n',
]


def create_sublime_project_file(project_name, project_dir):
    print('Creating sublime project file...')
    project_file = project_dir / '.sublime-project-files' / f'python-{project_name}.sublime-project'
    template = {
    "folders":
    [
        {
            "path": f"{project_file.parent.parent.as_posix()}"
        }
    ],
    "build_systems":
    [
        {
            "name": f"{project_name}",
            "target":"terminus_open",
            "title":f"{project_name}",
            "tag":"python",
            "auto_close": False,
            "focus": True,
            "timeit": False,
            "shell_cmd": "python -u \"$file\"",
            "file_regex": "^[ ]*File \"(...*?)\", line ([0-9]*)",
            "working_dir": "${file_path}",
            "file_patterns":["*.py"],
            "selector": "source.python",
            "env": {
                        "PATH": f"$PATH;{project_file.parent.parent.as_posix()}/.venv/Scripts",
                   }
        }
    ]
}
    with open(project_file, 'w') as f:
        json.dump(template, f, indent=4)


def get_project_name():
    print('Enter project name')
    project_name = None
    while not project_name:
        project_name = input('> ').strip()

    return project_name


def create_virtual_env(project_dir):
    print('Creating project virtual environment...')
    os.chdir(project_dir)
    subprocess.run(['python', '-m', 'venv', '.venv'])


def create_folders(project_dir, folders_to_create):
    print('Creating project folders...')
    # Create folders
    for folder_name in folders_to_create:
        sub_folder = project_dir / folder_name
        sub_folder.mkdir(parents=True, exist_ok=True)


def create_files(project_dir, files_to_create):
    print('Creating project files...')
    # Create files
    for filename in files_to_create:
        project_file = project_dir / filename
        project_file.touch()


def create_gitignore_file(project_dir, to_ignore_files):
    print('Creating .gitignore file...')
    # Create .gitignore file.
    with open(project_dir / '.gitignore', 'w') as f:
        f.writelines(to_ignore_files)


def create_new_project(project_name=None):
    if project_name is None:
        project_name = 'New Project'
    project_dir = MAIN_PROJECT_FOLDER / project_name
    project_dir.mkdir(exist_ok=True)

    create_virtual_env(project_dir)
    create_folders(project_dir, project_sub_folders)
    create_files(project_dir, project_files)
    create_gitignore_file(project_dir, ignored_files)
    create_sublime_project_file(project_name, project_dir)

    print('Done!')


if __name__ == '__main__':
    project_name = get_project_name()
    print(f'Creating new python project: {project_name} ...')
    create_new_project(project_name)
