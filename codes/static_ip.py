import subprocess
import re


def get_current_hotspot_ip(interface_name="Wi-Fi 2"):
    ipconfig_output = subprocess.check_output(["ipconfig"]).decode("utf-8")
    pattern = re.compile(fr"{interface_name}.*?IPv4 Address.*?: (.*?)\r", re.DOTALL | re.IGNORECASE)
    match = pattern.search(ipconfig_output)
    if match:
        return match.group(1)
    return None


def set_static_ip(new_ip, interface_name="Wi-Fi 2"):
    try:
        subprocess.run(["netsh", "interface", "ipv4", "set", "address", "name", interface_name, "static", new_ip, "255.255.255.0"], check=True)
        print(f"Updated FTP server IP address to {new_ip}")
    except subprocess.CalledProcessError as e:
        print(f"Error updating FTP server IP: {e}")


def main():
    hotspot_interface_name = "Wi-Fi 2"

    current_hotspot_ip = get_current_hotspot_ip()

    if current_hotspot_ip:
        set_ftp_server_ip(current_hotspot_ip, hotspot_interface_name)
    else:
        print("Hotspot IP not found. Unable to update FTP server IP.")


if __name__ == "__main__":
    main()
