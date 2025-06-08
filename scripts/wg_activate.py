#!/usr/bin/env python3
"""
WireGuard Configuration Activator - Improved Version
A robust script to activate WireGuard configurations with better status detection.
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

    def check_interface_status(self, interface_name):
        """Check if a WireGuard interface is active using multiple methods."""
        self.logger.debug(f"Checking status for interface: {interface_name}")

        # Method 1: Check with wg command
        try:
            result = subprocess.run(['sudo', 'wg', 'show', interface_name],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                self.logger.debug(f"wg show successful for {interface_name}")
                return "🟢 ACTIVE", result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.debug(f"wg command failed for {interface_name}: {e}")

        # Method 2: Check network interfaces
        try:
            result = subprocess.run(['ip', 'link', 'show', interface_name],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                if "UP" in result.stdout and "LOWER_UP" in result.stdout:
                    self.logger.debug(f"Interface {interface_name} is UP via ip command")
                    return "🟡 UP (No WG Data)", None
                elif "UP" in result.stdout:
                    return "🟠 UP (Link Down)", None
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.debug(f"ip command failed for {interface_name}: {e}")

        # Method 3: Check with systemctl (if using systemd)
        try:
            result = subprocess.run(['systemctl', 'is-active', f'wg-quick@{interface_name}'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip() == "active":
                self.logger.debug(f"systemd service active for {interface_name}")
                return "🟢 ACTIVE (systemd)", None
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.debug(f"systemctl command failed for {interface_name}: {e}")

        return "⚪ INACTIVE", None

    def display_configs(self):
        """Display available configurations with improved status detection."""
        self.logger.debug("Displaying configuration menu")
        print("\nAvailable WireGuard Configurations:")
        print("-" * 60)

        for i, config in enumerate(self.configs, 1):
            interface_name = config.stem
            status, wg_info = self.check_interface_status(interface_name)
            print(f"{i:2d}. {interface_name:<20} {status}")

        print(f"\n 0. Exit")
        print("-" * 60)

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
        """Activate the selected WireGuard configuration with improved error handling."""
        interface_name = config_path.stem

        self.logger.info(f"Attempting to activate WireGuard interface: {interface_name}")
        print(f"\nActivating WireGuard interface: {interface_name}")

        try:
            # First, deactivate any currently active interfaces
            self.logger.debug("Deactivating any existing WireGuard interfaces")
            self.deactivate_all(quiet=True)

            # Wait a moment for cleanup
            import time
            time.sleep(1)

            # Activate the selected configuration
            self.logger.debug(f"Bringing up interface: {interface_name}")
            result = subprocess.run(['sudo', 'wg-quick', 'up', interface_name],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                success_msg = f"Successfully activated {interface_name}"
                self.logger.info(success_msg)
                print(f"✅ {success_msg}")

                # Wait a moment for interface to fully initialize
                time.sleep(2)

                # Show detailed connection status
                self.show_interface_details(interface_name)

            else:
                error_msg = f"Failed to activate {interface_name}"
                self.logger.error(f"{error_msg}. Return code: {result.returncode}")
                print(f"❌ {error_msg}")

                if result.stderr:
                    self.logger.error(f"stderr: {result.stderr}")
                    print(f"Error details: {result.stderr}")
                if result.stdout:
                    self.logger.debug(f"stdout: {result.stdout}")
                    print(f"Output: {result.stdout}")

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout while activating {interface_name}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
        except FileNotFoundError as e:
            error_msg = "wg-quick command not found. Please install WireGuard."
            self.logger.error(f"{error_msg} Exception: {e}")
            print(f"❌ Error: {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")

    def show_interface_details(self, interface_name):
        """Show detailed information about a specific interface."""
        print(f"\n📊 Interface Details for {interface_name}:")
        print("=" * 50)

        # Check with multiple methods
        methods = [
            ("WireGuard Status", ['sudo', 'wg', 'show', interface_name]),
            ("Network Interface", ['ip', 'addr', 'show', interface_name]),
            ("Routing Info", ['ip', 'route', 'show', 'dev', interface_name]),
        ]

        for method_name, command in methods:
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    print(f"\n{method_name}:")
                    print(result.stdout.strip())
                else:
                    print(f"\n{method_name}: No data available")
            except Exception as e:
                print(f"\n{method_name}: Error - {e}")

    def deactivate_all(self, quiet=False):
        """Deactivate all active WireGuard interfaces."""
        if not quiet:
            self.logger.info("Starting deactivation of all WireGuard interfaces")
            print("\nDeactivating all WireGuard interfaces...")

        deactivated_count = 0
        for config in self.configs:
            interface_name = config.stem
            try:
                self.logger.debug(f"Attempting to deactivate interface: {interface_name}")
                result = subprocess.run(['sudo', 'wg-quick', 'down', interface_name],
                                      capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    success_msg = f"Deactivated {interface_name}"
                    self.logger.info(success_msg)
                    if not quiet:
                        print(f"✅ {success_msg}")
                    deactivated_count += 1
                else:
                    self.logger.debug(f"Interface {interface_name} was not active or failed to deactivate")
            except Exception as e:
                self.logger.error(f"Error deactivating {interface_name}: {e}")

        if not quiet:
            self.logger.info(f"Deactivation complete. {deactivated_count} interfaces deactivated.")

    def show_menu(self):
        """Show additional menu options."""
        print("\nAdditional Options:")
        print("d. Deactivate all interfaces")
        print("r. Refresh/reload configurations")
        print("s. Show current status")
        print("t. Test connectivity")
        print("q. Quit")

        choice = input("\nChoose an option (or number to activate): ").strip().lower()
        self.logger.debug(f"Menu choice: '{choice}'")
        return choice

    def show_status(self):
        """Show comprehensive status of all WireGuard interfaces."""
        self.logger.debug("Displaying comprehensive WireGuard status")
        print("\n🔍 Comprehensive WireGuard Status:")
        print("=" * 60)

        # Method 1: Try wg show all
        print("\n1. WireGuard Interface Status:")
        try:
            result = subprocess.run(['sudo', 'wg', 'show', 'all'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                if result.stdout.strip():
                    print(result.stdout)
                else:
                    print("   No active WireGuard interfaces found.")
            else:
                print(f"   Error getting WireGuard status (code: {result.returncode})")
                if result.stderr:
                    print(f"   Error: {result.stderr}")
        except Exception as e:
            print(f"   Error: {e}")

        # Method 2: Check all network interfaces
        print("\n2. Network Interface Status:")
        try:
            result = subprocess.run(['ip', 'link', 'show'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                wg_interfaces = [line for line in result.stdout.split('\n')
                               if any(config.stem in line for config in self.configs)]
                if wg_interfaces:
                    for line in wg_interfaces:
                        print(f"   {line.strip()}")
                else:
                    print("   No WireGuard network interfaces found.")
        except Exception as e:
            print(f"   Error: {e}")

        # Method 3: Individual interface check
        print("\n3. Individual Interface Status:")
        for config in self.configs:
            interface_name = config.stem
            status, _ = self.check_interface_status(interface_name)
            print(f"   {interface_name:<15} {status}")

    def test_connectivity(self):
        """Test connectivity through active WireGuard interfaces."""
        print("\n🌐 Testing Connectivity:")
        print("=" * 40)

        # Find active interfaces
        active_interfaces = []
        for config in self.configs:
            interface_name = config.stem
            status, _ = self.check_interface_status(interface_name)
            if "ACTIVE" in status or "UP" in status:
                active_interfaces.append(interface_name)

        if not active_interfaces:
            print("No active WireGuard interfaces found.")
            return

        print(f"Active interfaces: {', '.join(active_interfaces)}")

        # Test connectivity
        test_hosts = ["8.8.8.8", "1.1.1.1", "google.com"]

        for host in test_hosts:
            try:
                print(f"\nTesting connectivity to {host}...")
                result = subprocess.run(['ping', '-c', '3', '-W', '5', host],
                                      capture_output=True, text=True, timeout=20)
                if result.returncode == 0:
                    print(f"✅ {host} - Reachable")
                    # Extract ping time if available
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'time=' in line:
                            print(f"   Sample: {line.strip()}")
                            break
                else:
                    print(f"❌ {host} - Unreachable")
            except Exception as e:
                print(f"❌ {host} - Error: {e}")

    def run(self):
        """Main application loop with improved error handling."""
        self.logger.info("WireGuard Configuration Activator started")
        print("🔧 WireGuard Configuration Activator - Enhanced")
        print("=" * 50)

        while True:
            try:
                if not self.find_configs():
                    self.logger.error("No configurations found. Exiting.")
                    sys.exit(1)

                self.display_configs()
                choice = self.show_menu()

                if choice == 'q':
                    self.logger.info("User chose to quit")
                    print("👋 Goodbye!")
                    break
                elif choice == 'd':
                    self.logger.info("User chose to deactivate all interfaces")
                    self.deactivate_all()
                elif choice == 'r':
                    self.logger.info("User chose to refresh configurations")
                    print("🔄 Refreshing configurations...")
                    continue
                elif choice == 's':
                    self.logger.info("User chose to show status")
                    self.show_status()
                elif choice == 't':
                    self.logger.info("User chose to test connectivity")
                    self.test_connectivity()
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
                            print(f"❌ Please enter a number between 1 and {len(self.configs)}")
                    except ValueError:
                        self.logger.warning(f"Invalid menu option: '{choice}'")
                        print("❌ Invalid option. Please try again.")

                input("\n⏎ Press Enter to continue...")

            except KeyboardInterrupt:
                self.logger.info("User interrupted with Ctrl+C")
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                print(f"❌ Unexpected error: {e}")
                input("\n⏎ Press Enter to continue...")

        self.logger.info("WireGuard Configuration Activator ended")

def main():
    """Main entry point with improved argument handling."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WireGuard Configuration Activator - Enhanced Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Use default /etc/wireguard directory
  %(prog)s /path/to/configs          # Use custom configuration directory
  %(prog)s --log-level DEBUG         # Enable debug logging
  %(prog)s --quiet                   # Minimal output
        """
    )

    parser.add_argument('config_dir', nargs='?', default='/etc/wireguard',
                       help='Path to WireGuard configuration directory (default: /etc/wireguard)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Set logging level (default: INFO)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress console output except errors')
    parser.add_argument('--version', action='version', version='WireGuard Activator 2.0')

    args = parser.parse_args()

    # Set log level
    log_level = getattr(logging, args.log_level.upper())
    if args.quiet:
        log_level = logging.ERROR

    # Check if running as root for sudo operations
    if os.geteuid() != 0:
        print("ℹ️  Note: This script will use 'sudo' for WireGuard operations.")
        print("You may be prompted for your password.\n")

    try:
        activator = WireGuardActivator(args.config_dir, log_level)
        activator.run()
    except Exception as e:
        # Create a basic logger for critical errors
        logging.basicConfig(level=logging.ERROR)
        logger = logging.getLogger('WireGuardActivator')
        logger.error(f"Critical error in main: {e}", exc_info=True)
        print(f"💥 Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
