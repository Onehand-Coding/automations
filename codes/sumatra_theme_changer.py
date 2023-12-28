# SumatraPDF v3.4.6 64-bit Theme changer
import re
from pathlib import Path

SUMATRA_SETTINGS_FILE = Path("~/Appdata/Local/SumatraPDF/SumatraPDF-settings.txt").expanduser()

# List  of Sumatra settings for color customization.
COLOR_SETTINGS = [
    "TextColor",
    "BackgroundColor",
    "MainWindowBackground",
    "SelectionColor",
    "GradientColors",  # Must be added in advanced settings first.
]

#  Color themes. {setting: color}
LIGHT_COLORS = {
    "TextColor": "#000000",
    "BackgroundColor": "#ffffff",
    "MainWindowBackground": "#80fff200",
    "SelectionColor": "#f5fc0c",
    "GradientColors": "#2828aa #28aa28 #aa2828",
}
DARK_COLORS = {
    "TextColor": "#dddddd",
    "BackgroundColor": "#111111",
    "MainWindowBackground": "#2e2e2e",
    "SelectionColor": "#f5fc0c",
    "GradientColors": "#2828aa #28aa28 #aa2828",
}
DRACULA_COLORS = {
    "TextColor": "#f8f8f2",
    "BackgroundColor": "#21222c",
    "MainWindowBackground": "#282a36",
    "SelectionColor": "#f4f4f4",
    "GradientColors": "#2828aa #28aa28 #aa2828",
}


class SumatraColorException(Exception):
    """Exception for errors regarding sumatra color settings."""


class SumatraSetting:
    """A simple sumatraPDF color/theme modification class.
        Works for SumatraPDF v3.4.6 64-bit version."""

    def __init__(self, settingsFile):
        self.file = settingsFile
        self.currentTheme = {}

    def getCurrentSettings(self):
        with open(self.file, "r") as f:
            self.currentSettings = f.read()
            for colorSetting in COLOR_SETTINGS:
                try:
                    color = re.findall(r"%s = (.*)" % (colorSetting), self.currentSettings)[0]
                    if not color:
                        raise ValueError(f'No color found for {colorSetting}!')
                    self.currentTheme[colorSetting] = color
                except IndexError as e:
                    raise SumatraColorException(f'"{colorSetting}" is not defined in settings.') from e
                except ValueError as e:
                    raise SumatraColorException(f'No color found for {colorSetting} in settings.') from e

    def changeMode(self):
        self.newTheme = {
            tuple(LIGHT_COLORS.items()): DRACULA_COLORS,
            tuple(DRACULA_COLORS.items()): DARK_COLORS,
            tuple(DARK_COLORS.items()): LIGHT_COLORS,
        }.get(tuple(self.currentTheme.items()), LIGHT_COLORS)

    def update(self):
        self.changeMode()
        updatedSettings = []
        with open(self.file, "r+") as f:
            for line in f.readlines():
                for colorSetting in COLOR_SETTINGS:
                    currentColor = self.currentTheme[colorSetting]
                    newColor = self.newTheme[colorSetting]
                    line = re.sub(currentColor, newColor, line)
                updatedSettings.append(line)
            f.seek(0)
            f.writelines(updatedSettings)
            f.truncate()


def main():
    sumatraSetting = SumatraSetting(SUMATRA_SETTINGS_FILE)
    try:
        sumatraSetting.getCurrentSettings()
    except SumatraColorException as e:
        print(f'Something went wrong! {e}')
    except FileNotFoundError:
        print(f'Error! {sumatraSetting.file} not found!')
    except Exception as e:
        raise e
    else:
        sumatraSetting.update()


if __name__ == '__main__':
    main()
