import sys
import json
from pathlib import Path
import helper


def create_backup(settings_path, backup_path):
    """Make a backup copy of the original sumatra settings file."""
    with open(settings_path, 'r') as in_file, open(backup_path, 'w') as out_file:
        for line in in_file:
            out_file.write(line)


def update_db(db_file, db_key, data):
    """Update the backup database with new records."""
    with open(db_file, 'w') as db:
        json.dump({db_key: data}, db, indent=4)


def record_backup(db_file, backup_file, backup_time, db_key):
    """Record a backup in the backup database."""
    try:
        with open(db_file, 'r') as db:
            records = json.load(db).get(db_key)
            records.append({backup_file: backup_time})
            update_db(db_file, db_key, records)

    except FileNotFoundError:
        data = [{backup_file: backup_time}]
        update_db(db_file, db_key, data)


def get_backup_data(db_file, db_key):
    """Retrieve backup records from the backup database."""
    with open(db_file, 'r') as db:
        data = json.load(db).get(db_key)
        if not data:
            raise ValueError('No backups created yet!')
        return data


def get_backup_record(data, *, task=''):
    """Get a specific backup record from the user."""
    print(f'Choose backup file to {task}:')
    for index, record in enumerate(data, start=1):
        (backup_file, backup_time), = record.items()
        print(index, backup_file, backup_time)

    return data[helper.get_index(data)]


def create(settings_file, backup_db, backup_key):
    """Create a new backup for SumatraPDF settings."""
    backup_path = helper.new_filepath(settings_file, add_prefix='_backup')
    current_date = helper.get_str_datetime()
    try:
        create_backup(settings_file, backup_path)
        record_backup(backup_db, backup_path.name, current_date, backup_key)
        print('\nNew Sumatra settings backup created!\n')

    except Exception as e:
        print(f'Error: {e}!')


def revert(settings_folder, settings_file, backup_db, backup_key):
    """Revert SumatraPDF settings to a previous backup and remove it from backup database."""
    try:
        backup_data = get_backup_data(backup_db, backup_key)
    except (FileNotFoundError, ValueError):
        print('No backups to revert to!')
    else:
        backup_record = get_backup_record(backup_data, task='revert to')
        backup_file = settings_folder / list(backup_record)[0]
        backup_file.replace(settings_file)

        backup_data.remove(backup_record)
        update_db(backup_db, backup_key, backup_data)
        print(f'\nReverted to {backup_file.name} successfully!\n')


def delete(settings_folder, backup_db, backup_key):
    """Delete a specific backup and remove it from the backup database."""
    try:
        backup_data = get_backup_data(backup_db, backup_key)
    except (FileNotFoundError, ValueError) as e:
        print(e)
    else:
        backup_record = get_backup_record(backup_data, task='delete')
        backup_file, = backup_record.keys()
        backup_file = settings_folder / backup_file
        try:
            backup_file.unlink()
        except FileNotFoundError:
            print('Backup File not Found!')
        else:
            backup_data.remove(backup_record)
            update_db(backup_db, backup_key, backup_data)
            print(f'\nRemoved {backup_file.name} from backups!\n')


def execute_action(settings_folder, settings_file, backup_db, backup_key, action):
    """Execute the chosen action based on user input."""
    match action:
        case 'create':
            create(settings_file, backup_db, backup_key)
        case 'revert':
            revert(settings_folder, settings_file, backup_db, backup_key)
        case 'delete':
            delete(settings_folder, backup_db, backup_key)


def main():
    settings_folder = Path('~/AppData/Local/SumatraPDF').expanduser()
    settings_file = settings_folder / 'SumatraPDF-settings.txt'
    backup_db = settings_folder / 'backup_db.json'
    backup_key = 'backup records'
    if not settings_file.exists():
        print('Error, Sumatra settings file not found!')

    while True:
        action = helper.choose(['create', 'revert', 'delete'], task='action')
        execute_action(settings_folder, settings_file, backup_db, backup_key, action)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Bye!')
        sys.exit()
