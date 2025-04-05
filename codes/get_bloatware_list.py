#!/usr/bin/env python3

import argparse
from pathlib import Path

bloatwares = Path("/sdcard/Download") / "bloatwares.txt"  # Container file for the extracted uninstalled bloatwares.


def get_package_names(file):
    # Get package names from a file.
    with open(file, "r") as f:
        lines = f.readlines()
    return {line.strip() for line in lines}


def get_bloatwares(all_packages, third_party_packages, debloated_packages):
    # Extract the list of uninstalled bloatwares from the given files.
    with_bloatwares = get_package_names(all_packages) - get_package_names(third_party_packages)

    return with_bloatwares - get_package_names(debloated_packages)


def main():
    parser = argparse.ArgumentParser(description="Extract bloatware list from  given files.")
    parser.add_argument("all_packages", help="File containing currently installed system, third party, and those uninstalled system packages.")
    parser.add_argument("third_party_packages", help="File containing currently installed third party packages.")
    parser.add_argument("debloated_packages", help=" File containing currently installed system packages with those bloatwares uninstalled.")
    args = parser.parse_args()

    # Write the list of bloatware packages to a file.
    bloatware_list = [line + "\n" for line in sorted(get_bloatwares(args.all_packages, args.third_party_packages, args.debloated_packages))]
    with open(bloatwares, "w") as f:
            f.writelines(bloatware_list)
            

if __name__ == "__main__":
    main()
