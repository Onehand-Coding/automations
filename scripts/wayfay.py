import re
import sys
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from helper.funcs import write_to_json, read_print_json, DATA_DIR

def get_ssids() -> List[str]:
    """Get list of SSIDs of previous and present wifi connections of the device.
    Returns:
        List of SSIDs found in the system
    """
    print("Getting wifi SSIDs...")
    system = platform.system()

    try:
        if system == "Windows":
            result = subprocess.run(
                ["netsh", "wlan", "show", "profiles"],
                capture_output=True,
                text=True,
                check=True
            )
            ssids = re.findall(r"All User Profile\s+:\s+(.*)\r", result.stdout)
        elif system == "Darwin":  # macOS
            result = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
                capture_output=True,
                text=True,
                check=True
            )
            # Extract SSIDs from airport output (skipping header line)
            ssids = [line.split()[0] for line in result.stdout.splitlines()[1:] if line.strip()]
        elif system == "Linux":
            # Try nmcli first (most modern Linux distros)
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "name", "connection", "show"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                ssids = [line for line in result.stdout.splitlines() if line.strip()]
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fall back to looking in network manager files
                wifi_path = Path("/etc/NetworkManager/system-connections/")
                if wifi_path.exists():
                    ssids = [f.stem for f in wifi_path.glob("*") if f.is_file()]
                else:
                    ssids = []
        else:
            print(f"Unsupported operating system: {system}")
            return []

        return ssids

    except subprocess.CalledProcessError as e:
        print(f"Error retrieving SSIDs: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error getting SSIDs: {e}")
        return []

def get_passwords(ssids: List[str]) -> List[Dict[str, str]]:
    """Get passwords for each SSID.
    Args:
        ssids: List of SSIDs to retrieve passwords for
    Returns:
        List of dictionaries containing SSID and password pairs
    """
    print("Getting password for each SSID...")
    wifi_list = []
    system = platform.system()

    for ssid in ssids:
        wifi_info = {"SSID": ssid}
        try:
            if system == "Windows":
                result = subprocess.run(
                    ["netsh", "wlan", "show", "profile", ssid, "key=clear"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                password_match = re.search(r"Key Content\s+:\s+(.*)\r", result.stdout)
                wifi_info["Password"] = password_match.group(1) if password_match else "No password"

            elif system == "Darwin":  # macOS
                # macOS stores passwords in Keychain
                result = subprocess.run(
                    ["security", "find-generic-password", "-wa", ssid],
                    capture_output=True,
                    text=True,
                    check=False
                )
                password = result.stdout.strip()
                wifi_info["Password"] = password if password and not result.stderr else "No password"

            elif system == "Linux":
                # Try nmcli first
                try:
                    result = subprocess.run(
                        ["nmcli", "-s", "-g", "802-11-wireless-security.psk", "connection", "show", ssid],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    password = result.stdout.strip()
                    wifi_info["Password"] = password if password else "No password"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fall back to checking network manager files
                    wifi_path = Path("/etc/NetworkManager/system-connections/") / ssid
                    if wifi_path.exists():
                        try:
                            content = wifi_path.read_text()
                            password_match = re.search(r'psk=(.*)', content)
                            wifi_info["Password"] = password_match.group(1) if password_match else "No password"
                        except Exception:
                            wifi_info["Password"] = "Password exists but couldn't be read"
                    else:
                        wifi_info["Password"] = "No password"

            wifi_list.append(wifi_info)

        except UnicodeDecodeError:
            print(f"Skipping SSID '{ssid}' due to encoding issues")
            continue
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving password for SSID '{ssid}': {e}")
            continue
        except Exception as e:
            print(f"Unexpected error getting password for SSID '{ssid}': {e}")
            continue

    return wifi_list

def save_wifi_data(wifi_data: List[Dict[str, str]], output_file: Path) -> None:
    """Save wifi data to a JSON file.
    Args:
        wifi_data: List of dictionaries containing SSID and password pairs
        output_file: Path to the output JSON file
    """
    print(f"Writing wifi data to {output_file}...")
    write_to_json(output_file, "wifi_passwords", wifi_data)

def main() -> None:
    """Main function to retrieve and save wifi passwords."""

    # Get SSIDs and passwords
    ssids = get_ssids()
    if not ssids:
        print("No wifi profiles found.")
        return

    print(f"Found {len(ssids)} wifi profiles.")
    wifi_data = get_passwords(ssids)

    # Save data
    wifi_data_file = DATA_DIR / "wifi_passwords.json"
    save_wifi_data(wifi_data, wifi_data_file)

    # Display the saved data
    print("\nSaved wifi passwords:")
    read_print_json(wifi_data_file)

if __name__ == '__main__':
    main()
