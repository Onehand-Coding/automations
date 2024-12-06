from pathlib import Path

downloads = Path("/storage/emulated/0/Download")
all_packages = downloads / "all_packages.txt"
debloated_system_packages = downloads / "debloated_system_packages.txt"
third_party_packages = downloads / "third_party_packages.txt"
bloatwares = downloads / "bloatwares.txt"


def get_all_packages():
    with open(all_packages, "r") as f:
        all_packages_lines = f.readlines()
    return {line.strip() for line in all_packages_lines}


def get_debloated_system_packages():
    with open(debloated_system_packages, "r") as f:
        debloated_system_packages_lines = f.readlines()
    return {line.strip() for line in debloated_system_packages_lines}


def get_third_party_packages():
    with open(third_party_packages, "r") as f:
        third_party_packages_lines = f.readlines()
    return {line.strip() for line in third_party_packages_lines}


def get_bloatwares():
    with_bloatwares = get_all_packages() - get_third_party_packages()

    return with_bloatwares - get_debloated_system_packages()


def write_bloatwares():
    with open(bloatwares, "w") as f:
            bloatware_list = [line + "\n" for line in sorted(get_bloatwares())]
            f.writelines(bloatware_list)
            

#write_bloatwares()

