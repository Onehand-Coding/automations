import re
import csv
import json
import subprocess
from pathlib import Path


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


def writeToCsv(scriptDir, wifiData):
    print(f"Writing wifi data to csv file...")
    with open(scriptDir / "wifi_password.csv", "w", newline="") as f:
        fields = ["SSID", "Password"]
        csvWriter = csv.DictWriter(f, delimiter=",", fieldnames=fields)
        csvWriter.writeheader()

        for data in wifiData:
            csvWriter.writerow(data)


def writeToJson(scriptDir, wifiData):
    print(f"Writing wifi data to json file...")
    with open(scriptDir / "wifi_password.json", "w") as f:
        data = {"wifi passwords": wifiData}
        json.dump(data, f, indent=4)


def main():
    scriptsDataFolder = Path("~/.my scripts data").expanduser()
    if not scriptsDataFolder.exists():
        scriptsDataFolder.mkdir()

    myWifiData = getPasswords(getSSIDS())
    writeToCsv(scriptsDataFolder, myWifiData)
    writeToJson(scriptsDataFolder, myWifiData)
    print('Done!')


if __name__ == '__main__':
    main()
