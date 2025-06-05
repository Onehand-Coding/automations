#!/usr/bin/env python3
"""
WireGuard Configuration Activator
A simple script to activate WireGuard configurations with interactive selection.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime

from helper import setup_logging


class WireGuardActivator:
    def __init__(self, config_dir="/etc/wireguard", log_level=logging.INFO):
        self.config_dir = Path(config_dir)
        self.configs = []
        self.logger = setup_logging(log_file=f"wireguard_activator_{datetime.now().strftime('%Y%m%d')}.log")

    def find_configs(self):
        """Find all .conf files in the WireGuard directory."""
        self.logger.debug(f"Searching for configs in: {self.config_dir}")

        if not self.config_dir.exists():
            error_msg = f"WireGuard directory '{self.config_dir}' not found."
            self.logger.error(error_msg)
            print(f"Error: {error_msg}")
            print("Please make sure WireGuard is installed and configured.")
            return False

        self.configs = list(self.config_dir.glob("*.conf"))
        self.logger.debug(f"Found {len(self.configs)} configuration files")

        if not self.configs:
            warning_msg = f"No WireGuard configuration files found in '{self.config_dir}'"
            self.logger.warning(warning_msg)
            print(warning_msg)
            return False

        # Sort configs by filename
        self.configs.sort(key=lambda x: x.stem)
        config_names = [config.stem for config in self.configs]
        self.logger.info(f"Available configurations: {', '.join(config_names)}")
        return True

    def display_configs(self):
        """Display available configurations."""
        self.logger.debug("Displaying configuration menu")
        print("\nAvailable WireGuard Configurations:")
        print("-" * 40)
        for i, config in enumerate(self.configs, 1):
            # Get interface name (filename without .conf)
            interface_name = config.stem

            # Check if interface is currently active
            try:
                result = subprocess.run(['wg', 'show', interface_name],
                                      capture_output=True, text=True)
                status = "🟢 ACTIVE" if result.returncode == 0 else "⚪ INACTIVE"
                self.logger.debug(f"Interface {interface_name} status: {status}")
            except FileNotFoundError:
                status = "❓ UNKNOWN (wg tool not found)"
                self.logger.warning("wg command not found - cannot determine interface status")

            print(f"{i:2d}. {interface_name:<20} {status}")

        print(f"\n 0. Exit")
        print("-" * 40)

    def get_user_choice(self):
        """Get user's configuration choice."""
        while True:
            try:
                choice = input("\nSelect configuration to activate (number): ").strip()
                self.logger.debug(f"User input: '{choice}'")

                if choice == '0':
                    self.logger.info("User chose to exit")
                    return None

                choice_num = int(choice)
                if 1 <= choice_num <= len(self.configs):
                    selected_config = self.configs[choice_num - 1]
                    self.logger.info(f"User selected configuration: {selected_config.stem}")
                    return selected_config
                else:
                    error_msg = f"Invalid choice: {choice_num}. Please enter a number between 0 and {len(self.configs)}"
                    self.logger.warning(error_msg)
                    print(f"Please enter a number between 0 and {len(self.configs)}")

            except ValueError:
                self.logger.warning(f"Invalid input received: '{choice}'")
                print("Please enter a valid number")
            except KeyboardInterrupt:
                self.logger.info("User interrupted with Ctrl+C")
                print("\n\nExiting...")
                return None

    def activate_config(self, config_path):
        """Activate the selected WireGuard configuration."""
        interface_name = config_path.stem

        self.logger.info(f"Attempting to activate WireGuard interface: {interface_name}")
        print(f"\nActivating WireGuard interface: {interface_name}")

        try:
            # First, try to bring down any existing interface
            self.logger.debug(f"Attempting to bring down existing interface: {interface_name}")
            down_result = subprocess.run(['sudo', 'wg-quick', 'down', interface_name],
                          capture_output=True, text=True)

            if down_result.returncode == 0:
                self.logger.debug(f"Successfully brought down interface: {interface_name}")
            else:
                self.logger.debug(f"Interface {interface_name} was not active or failed to bring down")

            # Activate the selected configuration
            self.logger.debug(f"Bringing up interface: {interface_name}")
            result = subprocess.run(['sudo', 'wg-quick', 'up', interface_name],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                success_msg = f"Successfully activated {interface_name}"
                self.logger.info(success_msg)
                print(f"✅ {success_msg}")

                # Show connection status
                status_result = subprocess.run(['wg', 'show', interface_name],
                                             capture_output=True, text=True)
                if status_result.returncode == 0 and status_result.stdout.strip():
                    self.logger.debug(f"Interface status:\n{status_result.stdout}")
                    print(f"\nConnection Status:")
                    print(status_result.stdout)
                else:
                    status_msg = f"Interface {interface_name} is up but no peers connected yet."
                    self.logger.info(status_msg)
                    print(status_msg)

            else:
                error_msg = f"Failed to activate {interface_name}"
                self.logger.error(f"{error_msg}. Return code: {result.returncode}")
                if result.stderr:
                    self.logger.error(f"stderr: {result.stderr}")
                print(f"❌ {error_msg}")
                if result.stderr:
                    print(f"Error: {result.stderr}")

        except FileNotFoundError as e:
            error_msg = "wg-quick command not found. Please install WireGuard."
            self.logger.error(f"{error_msg} Exception: {e}")
            print(f"❌ Error: {error_msg}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Error executing command: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")

    def deactivate_all(self):
        """Deactivate all active WireGuard interfaces."""
        self.logger.info("Starting deactivation of all WireGuard interfaces")
        print("\nDeactivating all WireGuard interfaces...")

        deactivated_count = 0
        for config in self.configs:
            interface_name = config.stem
            try:
                self.logger.debug(f"Attempting to deactivate interface: {interface_name}")
                result = subprocess.run(['sudo', 'wg-quick', 'down', interface_name],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    success_msg = f"Deactivated {interface_name}"
                    self.logger.info(success_msg)
                    print(f"✅ {success_msg}")
                    deactivated_count += 1
                else:
                    self.logger.debug(f"Interface {interface_name} was not active or failed to deactivate")
            except Exception as e:
                self.logger.error(f"Error deactivating {interface_name}: {e}")

        self.logger.info(f"Deactivation complete. {deactivated_count} interfaces deactivated.")

    def show_menu(self):
        """Show additional menu options."""
        print("\nAdditional Options:")
        print("d. Deactivate all interfaces")
        print("r. Refresh/reload configurations")
        print("s. Show current status")
        print("q. Quit")

        choice = input("\nChoose an option (or number to activate): ").strip().lower()
        self.logger.debug(f"Menu choice: '{choice}'")
        return choice

    def show_status(self):
        """Show status of all WireGuard interfaces."""
        self.logger.debug("Displaying WireGuard status")
        print("\nWireGuard Status:")
        print("=" * 50)

        try:
            result = subprocess.run(['wg', 'show'], capture_output=True, text=True)
            if result.returncode == 0:
                if result.stdout.strip():
                    self.logger.debug("WireGuard status retrieved successfully")
                    print(result.stdout)
                else:
                    status_msg = "No active WireGuard interfaces."
                    self.logger.info(status_msg)
                    print(status_msg)
            else:
                error_msg = "Failed to get WireGuard status."
                self.logger.error(f"{error_msg} Return code: {result.returncode}")
                print(error_msg)
        except FileNotFoundError:
            error_msg = "wg command not found. Please install WireGuard tools."
            self.logger.error(error_msg)
            print(error_msg)

    def run(self):
        """Main application loop."""
        self.logger.info("WireGuard Configuration Activator started")
        print("WireGuard Configuration Activator")
        print("=" * 40)

        while True:
            if not self.find_configs():
                self.logger.error("No configurations found. Exiting.")
                sys.exit(1)

            self.display_configs()
            choice = self.show_menu()

            if choice == 'q':
                self.logger.info("User chose to quit")
                print("Goodbye!")
                break
            elif choice == 'd':
                self.logger.info("User chose to deactivate all interfaces")
                self.deactivate_all()
            elif choice == 'r':
                self.logger.info("User chose to refresh configurations")
                print("Refreshing configurations...")
                continue
            elif choice == 's':
                self.logger.info("User chose to show status")
                self.show_status()
            else:
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(self.configs):
                        selected_config = self.configs[choice_num - 1]
                        self.logger.info(f"User selected config {choice_num}: {selected_config.stem}")
                        self.activate_config(selected_config)
                    else:
                        error_msg = f"Invalid choice: {choice_num}"
                        self.logger.warning(error_msg)
                        print(f"Please enter a number between 1 and {len(self.configs)}")
                except ValueError:
                    self.logger.warning(f"Invalid menu option: '{choice}'")
                    print("Invalid option. Please try again.")

            input("\nPress Enter to continue...")

        self.logger.info("WireGuard Configuration Activator ended")

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="WireGuard Configuration Activator")
    parser.add_argument('config_dir', nargs='?', default='/etc/wireguard',
                       help='Path to WireGuard configuration directory (default: /etc/wireguard)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Set logging level (default: INFO)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress console output except errors')

    args = parser.parse_args()

    # Set log level
    log_level = getattr(logging, args.log_level.upper())
    if args.quiet:
        log_level = logging.ERROR

    # Check if running as root for sudo operations
    if os.geteuid() != 0:
        print("Note: This script will use 'sudo' for WireGuard operations.")
        print("You may be prompted for your password.\n")

    try:
        activator = WireGuardActivator(args.config_dir, log_level)
        activator.run()
    except Exception as e:
        # Create a basic logger for critical errors
        logging.basicConfig(level=logging.ERROR)
        logger = logging.getLogger('WireGuardActivator')
        logger.error(f"Critical error in main: {e}", exc_info=True)
        print(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
