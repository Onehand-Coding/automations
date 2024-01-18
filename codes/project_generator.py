from pathlib import Path

MAIN_PROJECT_FOLDER = Path('C:/coding/python/my_codes/projects')
PROJECT_SUB_FOLDERS = ['.sublime-project-files', 'codes', '.venv', 'logs', 'data']
PROJECT_FILES = ['.gitignore', 'README.md', 'requirements.txt']


def get_project_name():
    print('Enter project name')
    project_name = None
    while not project_name:
        project_name = input('> ').strip()

    return project_name


def create_new_project(project_name='New Project'):
    project_dir = MAIN_PROJECT_FOLDER / project_name

    # Create folders
    for folder_name in PROJECT_SUB_FOLDERS:
        sub_folder = project_dir / folder_name
        sub_folder.mkdir(parents=True, exist_ok=True)

    # Create files
    for filename in PROJECT_FILES:
        project_file = project_dir / filename
        project_file.touch()


if __name__ == '__main__':
    project_name = get_project_name()
    print(f'Creating new project {project_name}...')
    create_new_project(project_name)
