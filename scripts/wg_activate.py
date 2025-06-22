#!/usr/bin/env python3
"""
WireGuard Configuration Activator - Fixed Version
A robust script to activate WireGuard configurations with better sudo handling.
"""

import sys
import logging
import subprocess
import time
from pathlib import Path

from helper import setup_logging


class WireGuardActivator:
    def __init__(self, config_dir="/etc/wireguard", log_level=logging.INFO):
        self.config_dir = Path(config_dir)
        self.configs = []
        self.sudo_authenticated = False
        self.logger = setup_logging(
            log_file="wireguard_activator_.log"
        )

    def authenticate_sudo(self):
        """Authenticate sudo once at the beginning to avoid repeated prompts."""
        if self.sudo_authenticated:
            return True

        print("🔐 Authenticating sudo access...")
        print("Please enter your password when prompted:")

        try:
            # Test sudo access with a simple command
            result = subprocess.run(["sudo", "-v"], timeout=30)
            if result.returncode == 0:
                self.sudo_authenticated = True
                self.logger.info("Sudo authentication successful")
                print("✅ Sudo authentication successful")
                return True
            else:
                self.logger.error("Sudo authentication failed")
                print("❌ Sudo authentication failed")
                return False
        except subprocess.TimeoutExpired:
            self.logger.error("Sudo authentication timed out")
            print("❌ Sudo authentication timed out")
            return False
        except Exception as e:
            self.logger.error(f"Sudo authentication error: {e}")
            print(f"❌ Sudo authentication error: {e}")
            return False

    def run_sudo_command(self, command, timeout=30, capture_output=True):
        """Run a sudo command with proper error handling."""
        if not self.sudo_authenticated:
            if not self.authenticate_sudo():
                return None

        try:
            # Use sudo -n to avoid password prompts (non-interactive)
            sudo_command = ["sudo", "-n"] + command
            result = subprocess.run(
                sudo_command, capture_output=capture_output, text=True, timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(command)}")
            return None
        except Exception as e:
            self.logger.error(f"Error running command {' '.join(command)}: {e}")
            return None

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
            warning_msg = (
                f"No WireGuard configuration files found in '{self.config_dir}'"
            )
            self.logger.warning(warning_msg)
            print(warning_msg)
            return False

        # Sort configs by filename
        self.configs.sort(key=lambda x: x.stem)
        config_names = [config.stem for config in self.configs]
        self.logger.info(f"Available configurations: {', '.join(config_names)}")
        return True

    def check_interface_status(self, interface_name):
        """Check if a WireGuard interface is active."""
        self.logger.debug(f"Checking status for interface: {interface_name}")

        # Method 1: Check with wg command (most reliable)
        result = self.run_sudo_command(["wg", "show", interface_name], timeout=10)
        if result and result.returncode == 0 and result.stdout.strip():
            self.logger.debug(f"wg show successful for {interface_name}")
            return "🟢 ACTIVE", result.stdout.strip()

        # Method 2: Check network interfaces (fallback)
        try:
            result = subprocess.run(
                ["ip", "link", "show", interface_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                if "UP" in result.stdout and "LOWER_UP" in result.stdout:
                    self.logger.debug(
                        f"Interface {interface_name} is UP via ip command"
                    )
                    return "🟡 UP (No WG Data)", None
                elif "UP" in result.stdout:
                    return "🟠 UP (Link Down)", None
        except Exception as e:
            self.logger.debug(f"ip command failed for {interface_name}: {e}")

        return "⚪ INACTIVE", None

    def display_configs(self):
        """Display available configurations with status."""
        self.logger.debug("Displaying configuration menu")
        print("\n" + "=" * 60)
        print("Available WireGuard Configurations:")
        print("=" * 60)

        for i, config in enumerate(self.configs, 1):
            interface_name = config.stem
            status, _ = self.check_interface_status(interface_name)
            print(f"{i:2d}. {interface_name:<20} {status}")

        print("\n 0. Exit")
        print("=" * 60)

    def get_user_input(self, prompt):
        """Get user input with proper terminal handling."""
        try:
            # Reset terminal state
            sys.stdout.flush()
            sys.stderr.flush()
            return input(prompt).strip()
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Goodbye!")
            return None
        except EOFError:
            print("\n\n👋 EOF received. Goodbye!")
            return None

    def show_menu(self):
        """Show additional menu options."""
        print("\nAdditional Options:")
        print("d. Deactivate all interfaces")
        print("r. Refresh/reload configurations")
        print("s. Show current status")
        print("t. Test connectivity")
        print("q. Quit")

        choice = self.get_user_input("\nChoose an option (or number to activate): ")
        if choice is None:
            return "q"

        self.logger.debug(f"Menu choice: '{choice}'")
        return choice.lower()

    def activate_config(self, config_path):
        """Activate the selected WireGuard configuration."""
        interface_name = config_path.stem

        self.logger.info(
            f"Attempting to activate WireGuard interface: {interface_name}"
        )
        print(f"\n🔄 Activating WireGuard interface: {interface_name}")

        # First, deactivate any currently active interfaces
        print("📤 Deactivating existing interfaces...")
        self.deactivate_all(quiet=True)

        # Wait a moment for cleanup
        time.sleep(1)

        # Activate the selected configuration
        print(f"📥 Bringing up interface: {interface_name}")
        result = self.run_sudo_command(["wg-quick", "up", interface_name], timeout=45)

        if result and result.returncode == 0:
            success_msg = f"Successfully activated {interface_name}"
            self.logger.info(success_msg)
            print(f"✅ {success_msg}")

            # Wait a moment for interface to fully initialize
            time.sleep(2)

            # Show connection status
            self.show_interface_details(interface_name)

        else:
            error_msg = f"Failed to activate {interface_name}"
            self.logger.error(f"{error_msg}")
            print(f"❌ {error_msg}")

            if result and result.stderr:
                self.logger.error(f"stderr: {result.stderr}")
                print(f"Error details: {result.stderr}")
            elif result and result.stdout:
                self.logger.debug(f"stdout: {result.stdout}")
                print(f"Output: {result.stdout}")
            elif not result:
                print("Command failed or timed out.")

    def show_interface_details(self, interface_name):
        """Show detailed information about a specific interface."""
        print(f"\n📊 Interface Details for {interface_name}:")
        print("=" * 50)

        # WireGuard status
        print("\n🔍 WireGuard Status:")
        result = self.run_sudo_command(["wg", "show", interface_name], timeout=10)
        if result and result.returncode == 0 and result.stdout.strip():
            print(result.stdout.strip())
        else:
            print("   No WireGuard data available")

        # Network interface status
        print("\n🌐 Network Interface:")
        try:
            result = subprocess.run(
                ["ip", "addr", "show", interface_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                print(result.stdout.strip())
            else:
                print("   No network interface data available")
        except Exception as e:
            print(f"   Error getting network info: {e}")

    def deactivate_all(self, quiet=False):
        """Deactivate all active WireGuard interfaces."""
        if not quiet:
            self.logger.info("Starting deactivation of all WireGuard interfaces")
            print("\n📤 Deactivating all WireGuard interfaces...")

        deactivated_count = 0
        for config in self.configs:
            interface_name = config.stem

            # Check if interface is active first
            status, _ = self.check_interface_status(interface_name)
            if "ACTIVE" not in status and "UP" not in status:
                continue

            result = self.run_sudo_command(
                ["wg-quick", "down", interface_name], timeout=20
            )
            if result and result.returncode == 0:
                success_msg = f"Deactivated {interface_name}"
                self.logger.info(success_msg)
                if not quiet:
                    print(f"✅ {success_msg}")
                deactivated_count += 1
            else:
                if not quiet:
                    print(f"⚠️  {interface_name} was not active or failed to deactivate")

        if not quiet:
            print(
                f"\n📊 Deactivation complete. {deactivated_count} interfaces deactivated."
            )

    def show_status(self):
        """Show comprehensive status of all WireGuard interfaces."""
        self.logger.debug("Displaying comprehensive WireGuard status")
        print("\n🔍 Comprehensive WireGuard Status:")
        print("=" * 60)

        # Show all active WireGuard interfaces
        print("\n1. Active WireGuard Interfaces:")
        result = self.run_sudo_command(["wg", "show", "all"], timeout=15)
        if result and result.returncode == 0:
            if result.stdout.strip():
                print(result.stdout)
            else:
                print("   No active WireGuard interfaces found.")
        else:
            print("   Error getting WireGuard status")

        # Show individual interface status
        print("\n2. Individual Interface Status:")
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
            print("❌ No active WireGuard interfaces found.")
            return

        print(f"🟢 Active interfaces: {', '.join(active_interfaces)}")

        # Test connectivity
        test_hosts = ["8.8.8.8", "1.1.1.1"]

        for host in test_hosts:
            try:
                print(f"\n🔍 Testing connectivity to {host}...")
                result = subprocess.run(
                    ["ping", "-c", "3", "-W", "5", host],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                if result.returncode == 0:
                    print(f"✅ {host} - Reachable")
                    # Extract ping statistics
                    lines = result.stdout.split("\n")
                    for line in lines:
                        if "packet loss" in line or "min/avg/max" in line:
                            print(f"   {line.strip()}")
                else:
                    print(f"❌ {host} - Unreachable")
            except Exception as e:
                print(f"❌ {host} - Error: {e}")

    def run(self):
        """Main application loop."""
        self.logger.info("WireGuard Configuration Activator started")
        print("🔧 WireGuard Configuration Activator - Enhanced")
        print("=" * 50)

        # Authenticate sudo once at the start
        if not self.authenticate_sudo():
            print("❌ Failed to authenticate sudo. Exiting.")
            return

        while True:
            try:
                if not self.find_configs():
                    self.logger.error("No configurations found. Exiting.")
                    sys.exit(1)

                self.display_configs()
                choice = self.show_menu()

                if choice == "q" or choice is None:
                    self.logger.info("User chose to quit")
                    print("👋 Goodbye!")
                    break
                elif choice == "d":
                    self.logger.info("User chose to deactivate all interfaces")
                    self.deactivate_all()
                elif choice == "r":
                    self.logger.info("User chose to refresh configurations")
                    print("🔄 Refreshing configurations...")
                    continue
                elif choice == "s":
                    self.logger.info("User chose to show status")
                    self.show_status()
                elif choice == "t":
                    self.logger.info("User chose to test connectivity")
                    self.test_connectivity()
                else:
                    try:
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(self.configs):
                            selected_config = self.configs[choice_num - 1]
                            self.logger.info(
                                f"User selected config {choice_num}: {selected_config.stem}"
                            )
                            self.activate_config(selected_config)
                        else:
                            error_msg = f"Invalid choice: {choice_num}"
                            self.logger.warning(error_msg)
                            print(
                                f"❌ Please enter a number between 1 and {len(self.configs)}"
                            )
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
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="WireGuard Configuration Activator - Enhanced Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Use default /etc/wireguard directory
  %(prog)s /path/to/configs          # Use custom configuration directory
  %(prog)s --log-level DEBUG         # Enable debug logging
        """,
    )

    parser.add_argument(
        "config_dir",
        nargs="?",
        default="/etc/wireguard",
        help="Path to WireGuard configuration directory (default: /etc/wireguard)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "--version", action="version", version="WireGuard Activator 2.1"
    )

    args = parser.parse_args()

    # Set log level
    log_level = getattr(logging, args.log_level.upper())

    try:
        activator = WireGuardActivator(args.config_dir, log_level)
        activator.run()
    except Exception as e:
        # Create a basic logger for critical errors
        logging.basicConfig(level=logging.ERROR)
        logger = logging.getLogger("WireGuardActivator")
        logger.error(f"Critical error in main: {e}", exc_info=True)
        print(f"💥 Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
