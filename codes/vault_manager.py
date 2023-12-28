# text based vault manager.
import re
import csv
import json
import sys
import random
from pathlib import Path
import pyperclip

from helper import confirm, get_index

SCRIPTS_DATA_FOLDER = Path("~/.my scripts data").expanduser()
MY_VAULT = SCRIPTS_DATA_FOLDER / "my_accounts_vault.json"
BITWARDEN_FILES = [file for file in SCRIPTS_DATA_FOLDER.iterdir() if file.name.startswith("bitwarden_export")]
BITWARDEN_ACCOUNT_KEY = "items"
LOGINS_KEY = 'logins'
REOVERY_CODES_KEY = 'recovery codes'


class VaultException(Exception):
    """Exceptions for vault operation errors."""


class Vault:
    def __init__(self, file):
        self._database = file
        self.keys = [key for key in self.database]

    @property
    def database(self):
        with open(self._database, "r") as f:
            try:
                return json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise VaultException("Error Decoding vault JSON file!") from e

    def get_key(self):
        print(f'choose vault to access:')
        for index, key in enumerate(self.keys, start=1):
            print(index, key)
        return self.keys[get_index(self.keys)]

    def add_data(self):
        print("vault key:")
        vault_key = input("> ").strip()
        platform, value = get_details(k_input="platform: ", v_input="value: ")
        self.update(vault_key, [{platform: value}])
        print(f'{vault_key} added to vault!\n')

    def del_data(self, key):
        database = self.database
        del database[key]
        if confirm(f'remove {key} from vault?'):
            self.save(database)
        print(f'{key} removed from vault!\n')

    def save(self, data):
        with open(self._database, "w") as f:
            json.dump(data, f, indent=4)

    def update(self, key, new_data):
        if new_data:
            assert isinstance(new_data[0], dict)
        database = self.database
        database[key] = sorted(new_data, key=lambda x: list(x)[0].lower())
        self.save(database)


class VaultData:
    def __init__(self, key, vault):
        self.name = key
        self.vault = vault
        self.items = self.vault.database[key]

    def get_item(self):
        if self.name == LOGINS_KEY:
            self.get_logins()
        elif self.name == REOVERY_CODES_KEY:
            self.get_recovery()
        else:
            self.get_others()

    def add_item(self):
        if self.name == LOGINS_KEY:
            self.add_logins()
        elif self.name == REOVERY_CODES_KEY:
            self.add_recovery()
        else:
            self.add_others()
        self.vault.update(self.name, self.items)

    def del_item(self):
        if self.name == LOGINS_KEY:
            self.del_logins()
        elif self.name == REOVERY_CODES_KEY:
            self.del_recovery()
        else:
            self.del_others()
        self.vault.update(self.name, self.items)

    def get_data(self):
        print(f'\nchoose {self.name} platform:\n')
        for index, item in enumerate(self.items, start=1):
            print(index, self.extract_key(item))

        return self.items[get_index(self.items)]

    def get_logins(self):
        def get_account(accounts):
            if len(accounts) == 1:
                account_data = accounts[0]
            else:
                print('Choose account:')
                for index, account in enumerate(accounts, start=1):
                    print(index, self.extract_key(account))
                account_data = accounts[get_index(accounts)]

            username = self.extract_key(account_data)
            password = account_data.get(username)
            return (username, password)

        if len(self.items) == 1:
            login_data = self.items[0]
        else:
            login_data = self.get_data()
            login_platform = self.extract_key(login_data)
            url = login_data[login_platform]['url']
            accounts = login_data[login_platform]['accounts']
            username, password = get_account(accounts)

            print('what do you want to get?')
            print('url, username, password?')
            details = {'url': url, 'username': username, 'password': password}
            detail = input('> ').lower()
            try:
                info = details[detail]
            except KeyError:
                print('choose account info to get.')
            else:
                pyperclip.copy(info)
                print(f'{detail} for {login_platform} copied to clipboard!\n')

    def add_logins(self):
        if confirm('New login data?'):
            platform, url, username, password = get_details(new_logins=True)
            self.items.append(self.new_logins((platform, url, username, password)))
            print(f'{platform} added to {self.name} vault!')

        elif confirm('New account?'):
            login_data = self.get_data()
            login_platform = self.extract_key(login_data)
            accounts = login_data[login_platform].get('accounts')
            username, password = get_details()
            accounts.append({username: password})
            print(f'{username} added to {login_platform}')

        elif confirm('From bitwarden?'):
            for btwdnFile in BITWARDEN_FILES:
                self.add_from_bitwarden(btwdnFile)
            print(f'login details from bitwarden added to vault!\n')

        self.items.sort(key=lambda x: self.extract_key(x).lower())

    def del_logins(self):
        def del_account(platform, accounts):
            if len(accounts) == 1:
                account = accounts[0]
            else:
                print('choose account to delete:')
                for index, account in enumerate(accounts, start=1):
                    print(index, self.extract_key(account))
                account = accounts[get_index(accounts)]

            username = self.extract_key(account)
            if confirm(f'Remove {username} from {platform}?'):
                accounts.remove(account)
                print(f'{username} removed from {platform}!\n')

        login_data = self.get_data()
        login_platform = self.extract_key(login_data)

        if confirm('Delete this platform?'):
            self.items.remove(login_data)
            print(f'{login_platform} removed from {self.name} vault!')
        else:
            accounts = login_data[login_platform].get('accounts')
            del_account(login_platform, accounts)

        self.items.sort(key=lambda x: self.extract_key(x).lower())

    def get_recovery(self):
        recovery_data = self.get_data()
        recovery_platform = self.extract_key(recovery_data)
        recovery_codes = recovery_data.get(recovery_platform)
        recovery_code = random.choice(recovery_codes)
        pyperclip.copy(recovery_code)

        print(f'A recovery code for {recovery_platform} copied to clipboard!\n')
        print('this recovery code can only be used once.')
        if confirm('\nDelete?'):
            recovery_codes.remove(recovery_code)
            self.vault.update(self.name, self.items)

    def add_recovery(self):
        platform, codes = get_details(k_input='platform: ', v_input='recovery codes: ')
        self.items.append({platform: re.split(r'\s+|[,.:;-]\s*', codes)})

    def del_recovery(self):
        recovery_data = self.get_data()
        if confirm(f'Remove {self.extract_key(recovery_data)} from {self.name}?'):
            self.items.remove(recovery_data)

    def get_others(self):
        if len(self.items) == 1:
            item_data = self.items[0]
        else:
            item_data = self.get_data()
        item_key = self.extract_key(item_data)
        item_value = item_data.get(item_key)
        pyperclip.copy(item_value)
        print(f'{item_key} data copied to clipboard!\n')

    def add_others(self):
        key, value = get_details(k_input='key: ', v_input='value: ')
        self.items.append({key: value})
        self.vault.update(self.name, self.items)
        print(f'{key} added to {self.name} vault!\n')

    def del_others(self):
        if not self.items:
            print(f'{self.name} vault is empty!')
            return
        if len(self.items) == 1:
            item_data = self.items[0]
        elif len(self.items) > 1:
            item_data = self.get_data()
        if confirm(f'Delete {self.extract_key(item_data)} from {self.name}?'):
            self.items.remove(item_data)
            print(f'{self.extract_key(item_data)} Removed from {self.name} vault!\n')

    def add_from_bitwarden(self, btwdn_file):
        for platform, url, username, password in self.get_btwdn_data(btwdn_file):
            existing_platforms = [platform for account in self.items for platform in account]

            if platform in existing_platforms:
                acc_data = self.items[existing_platforms.index(platform)].get(platform)
                accounts = acc_data.get("accounts")
                accounts.sort(key=lambda x: list(x)[0].lower())
                if not any(username in account for account in accounts):
                    accounts.append({username: password})
                else:
                    accounts = [account for account in accounts if username in account]
                    old_password = accounts[0].get(username)
                    if old_password != password and confirm(f'Update password for {username}?'):
                        accounts[accounts.index({username: old_password})][username] = password
            else:
                self.items.append(self.new_logins((platform, url, username, password)))

        self.items.sort(key=lambda x: list(x)[0].lower())

    @staticmethod
    def extract_key(data):
        return list(data.keys())[0]

    @staticmethod
    def new_logins(acc_details):
        platform, url, username, password = acc_details
        return {platform: {"url": url, "accounts": [{username: password}]}}

    @staticmethod
    def get_btwdn_data(btwdn_file):
        with open(btwdn_file, "r") as f:
            if btwdn_file.suffix == ".csv":
                try:
                    csv_reader = csv.DictReader(f)
                    for account_data in csv_reader:
                        platform = account_data["name"]
                        url = account_data["login_uri"]
                        username = account_data["login_username"]
                        password = account_data["login_password"]
                        yield (platform, url, username, password)
                except Exception as e:
                    raise VaultException("Bitwarden CSV file error!") from e
            elif btwdn_file.suffix == ".json":
                try:
                    bitwdn_accounts = json.load(f).get(BITWARDEN_ACCOUNT_KEY)
                    for data in bitwdn_accounts:
                        platform = data.get("name")
                        account_info = data.get("login")
                        username = account_info.get("username")
                        password = account_info.get("password")
                        for info in account_info.get("uris"):
                            url = info.get("uri")
                        yield (platform, url, username, password)
                except json.decoder.JSONDecodeError as e:
                    raise VaultException("Error decoding Bitwarden JSON file!") from e


def get_action():
    action = None
    actions = ("get", "add", "del", 'delete vault', 'new vault', 'q')
    print('Choose action:')
    print("\nget, add, or del ?\n")
    while action not in actions:
        action = input("> ").lower().strip()
    return action


def get_details(*, new_logins=False, k_input="username: ", v_input="password: "):
    while True:
        if new_logins:
            platform = input("platform: ").strip()
            url = input("url: ").strip()
        key = input(k_input).strip()
        value = input(v_input).strip()
        if new_logins and all((platform, url, key, value)):
            return (platform, url, key, value)
        if not new_logins and all((key, value)):
            return (key, value)
        print("fill in details!")


def main():
    while True:
        my_vault = Vault(MY_VAULT)
        action = get_action()
        if action not in ('new vault', 'q'):
            key = my_vault.get_key()
            vault_data = VaultData(key, my_vault)
        match action:
            case 'get':
                vault_data.get_item()
            case 'add':
                vault_data.add_item()
            case 'del':
                vault_data.del_item()
            case 'new vault':
                my_vault.add_data()
            case 'delete vault':
                my_vault.del_data(key)
            case 'q':
                print('Bye!')
                sys.exit()


if __name__ == "__main__":
    try:
        main()
    except VaultException as err:
        print(f'Something went wrong, {err}')
    except KeyboardInterrupt:
        print('Bye!')
        sys.exit()
