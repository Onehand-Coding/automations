import sys
import json
from pathlib import Path
import helper


def create_backup(settings_path, backup_path):
    with open(settings_path, 'r') as in_file, open(backup_path, 'w') as out_file:
        for line in in_file:
            out_file.write(line)


def revert(frm_file, to_file):
    frm_file.replace(to_file)


def get_action():
    print('Pick backup action:')
    print('create, revert, or delete ?')
    while True:
        action = input('> ').lower()
        if action not in ('create', 'revert', 'delete'):
            continue
        return action


def update_db(db_file, db_key, data):
    with open(db_file, 'w') as db:
        json.dump({db_key: data}, db, indent=4)


def record_backup(db_file, backup_file, backup_time, db_key):
    try:
        with open(db_file, 'r') as db:
            records = json.load(db).get(db_key)
            records.append({backup_file: backup_time})
            update_db(db_file, db_key, records)

    except FileNotFoundError:
        data = [{backup_file: backup_time}]
        update_db(db_file, db_key, data)


def get_backup_data(db_file, db_key):
    with open(db_file, 'r') as db:
        data = json.load(db).get(db_key)
        if not data:
            raise ValueError('No backup file created yet!')
        return data


def get_backup_record(data, *, task=''):
    print(f'Choose backup file to {task}:\n')
    for index, record in enumerate(data, start=1):
        (backup_file, backup_time), = record.items()
        print(index, backup_file, backup_time)

    return data[helper.get_index(data)]


def main():
    settings_folder = Path('~/AppData/Local/SumatraPDF').expanduser()
    settings_file = settings_folder / 'SumatraPDF-settings.txt'
    backup_db = settings_folder / 'backup_db.json'
    backup_key = 'backup records'
    action = get_action()

    match action:
        case 'create':
            backup_path = helper.new_filepath(settings_folder, settings_file, name_ext='_backup')
            current_date = helper.get_current_date()
            try:
                create_backup(settings_file, backup_path)
            except FileNotFoundError:
                print('Failed to create backup, SumatraPDF-settings file not Found!')
            else:
                record_backup(backup_db, backup_path.name, current_date, backup_key)
                print('New Sumatra settings backup created!')
        case 'revert':
            try:
                backup_data = get_backup_data(backup_db, backup_key)
            except (FileNotFoundError, ValueError):
                print('No backup file/s to revert to!')
            else:
                backup_record = get_backup_record(backup_data, task='revert to')
                backup_file = settings_folder / list(backup_record)[0]
                revert(backup_file, settings_file)

                backup_data.remove(backup_record)
                update_db(backup_db, backup_key, backup_data)
                print(f'Reverted to {backup_file.name} successfully!')
        case 'delete':
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
                    print(f'Removed {backup_file.name} from backups!')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Bye!')
        sys.exit()
