import re
import subprocess
from pathlib import Path
from helper import write_to_json, read_print_json


def getSSIDS():
    """Return the list ssid of previous and present wifi connections of the device."""
    print("Getting wifi ssids...")
    wifiProfiles = subprocess.run(
        ["netsh", "wlan", "show", "profiles"], capture_output=True
    ).stdout.decode()

    wifissids = re.findall(r"All User Profile     : (.*)\r", wifiProfiles)

    return wifissids


def getPasswords(ssids):
    """Return a list of ssid and password dictionary."""
    print("Getting password of each ssids...")

    wifiList = []
    for ssid in ssids:
        wifissidAndPassword = {}
        wifissidAndPassword["SSID"] = ssid

        try:  # Wifi name/ssid's can be named with characters that cannot be decoded by .decode() method.
            output = subprocess.run(
                ["netsh", "wlan", "show", "profile", ssid, "key=clear"], capture_output=True,).stdout.decode()
        except UnicodeDecodeError:
            continue

        password = re.findall(r"Key Content            : (.*)\r", output)
        if not password:
            wifissidAndPassword["Password"] = "No password"
        else:
            wifissidAndPassword["Password"] = password[0]

        wifiList.append(wifissidAndPassword)

    return wifiList


def main():
    scriptsDataFolder = Path("~/.my scripts data").expanduser()
    if not scriptsDataFolder.exists():
        scriptsDataFolder.mkdir()

    myWifiData = getPasswords(getSSIDS())
    wifiDataFile = scriptsDataFolder / "wifi_password.json"
    wifiDataKey = "wifi passwords"

    print(f"Writing wifi data to json file...")
    write_to_json(wifiDataFile, wifiDataKey, myWifiData)
    read_print_json(wifiDataFile)
    print('Done!')


if __name__ == '__main__':
    main()
