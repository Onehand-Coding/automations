#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime
import argparse
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import shutil
import logging
import logging.handlers
import sys
import json # Needed for parsing rclone lsjson output

# Load environment variables
load_dotenv()

# --- Define constants near the top ---
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
CREDENTIALS_DIR = ROOT_DIR / "scripts/data/pg_backups"
BACKUP_DB_DIR = CREDENTIALS_DIR / "db"
DEFAULT_RCLONE_TARGET_DIR = "DB_Backups"
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "backup_tool.log"

# --- Setup Logging ---
# (Setup logging function remains the same as the previous version)
def setup_logging():
    """Configures logging to file and console."""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger() # Get root logger
    # Prevent adding handlers multiple times if script is re-run in same process
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO) # Set minimum level for logger

        # Ensure log directory exists
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # File Handler (Rotating)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.DEBUG) # Log DEBUG level and above to file

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging.INFO) # Log INFO level and above to console

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    # Get logger specific to this module
    module_logger = logging.getLogger(__name__)
    return module_logger

logger = setup_logging()

# --- Rclone Helper Functions ---
def check_rclone():
    """Checks if rclone exists and returns path or None."""
    rclone_path = shutil.which("rclone")
    if not rclone_path:
        error_msg = "rclone command not found. Please install rclone and ensure it's in your system's PATH."
        logger.error(error_msg)
        # No notification here, functions calling this should handle it
        return None
    return rclone_path

def download_latest_from_gdrive(rclone_remote_name, remote_dir_name, local_dest_dir):
    """Finds and downloads the latest .dump file from rclone remote."""
    logger.info(f"Checking remote '{rclone_remote_name}:{remote_dir_name}' for latest backup...")
    rclone_path = check_rclone()
    if not rclone_path:
        send_notification("GDrive Restore Failed", "rclone not found, cannot check remote.")
        return None

    remote_path = f"{rclone_remote_name}:{remote_dir_name}"
    command = [rclone_path, "lsjson", remote_path, "--files-only"]

    try:
        logger.debug(f"Executing rclone command: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        files_json = json.loads(result.stdout)

        dump_files = [f for f in files_json if f.get("Name", "").endswith(".dump")]

        if not dump_files:
            logger.warning(f"No .dump files found in remote directory '{remote_path}'.")
            return None

        # Find the latest file based on ModTime
        latest_file_meta = max(dump_files, key=lambda f: f.get("ModTime", ""))
        latest_filename = latest_file_meta.get("Name")
        remote_file_path = f"{remote_path}/{latest_filename}"
        local_file_path = Path(local_dest_dir) / latest_filename

        logger.info(f"Latest remote backup found: '{latest_filename}'. Attempting download...")

        download_command = [
            rclone_path, "copyto", "--progress", "--verbose",
            remote_file_path,
            str(local_file_path)
        ]
        logger.info(f"Executing rclone command: {' '.join(download_command)}")
        dl_result = subprocess.run(download_command, check=True, capture_output=True, text=True, encoding='utf-8')

        logger.info(f"✓ Successfully downloaded '{latest_filename}' to '{local_dest_dir}'.")
        logger.debug("rclone download stdout:\n---\n%s\n---", dl_result.stdout.strip())
        if dl_result.stderr:
            logger.debug("rclone download stderr:\n---\n%s\n---", dl_result.stderr.strip())
        return str(local_file_path)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse rclone lsjson output: {e}")
        logger.debug("rclone stdout for lsjson:\n%s", result.stdout)
        send_notification("GDrive Restore Failed", "Failed to parse rclone output.")
        return None
    except subprocess.CalledProcessError as e:
        error_details = f"rclone command failed (lsjson or copyto) with exit code {e.returncode}.\nStderr:\n{e.stderr}\nStdout:\n{e.stdout}"
        logger.error(f"GDrive download/check failed.\n{error_details}")
        send_notification("GDrive Restore Failed", error_details)
        return None
    except Exception as e:
        logger.exception("An unexpected error occurred during GDrive latest backup check/download.")
        send_notification("GDrive Restore Failed (Unexpected)", f"Error: {e}\nCheck logs.")
        return None


# --- Upload Function using rclone ---
# (upload_backup_with_rclone function remains the same as the previous version)
def upload_backup_with_rclone(local_file_path, rclone_remote_name, target_dir_name=DEFAULT_RCLONE_TARGET_DIR):
    """Uploads the backup file to a specific directory on an rclone remote."""
    local_file_path = Path(local_file_path)
    logger.info(f"Attempting upload via rclone to remote '{rclone_remote_name}', directory '{target_dir_name}'...")

    rclone_path = check_rclone() # Use helper
    if not rclone_path:
        send_notification("Upload FAILED (rclone)", "rclone command not found.")
        return False

    destination = f"{rclone_remote_name}:{target_dir_name}/"
    command = [
        rclone_path, "copyto", "--drive-skip-gdocs",
        "--progress", "--verbose",
        str(local_file_path),
        destination + local_file_path.name
    ]

    logger.info(f"Executing rclone command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            check=True, capture_output=True, text=True, encoding='utf-8'
        )
        logger.info("✓ rclone upload successful!")
        logger.debug("rclone stdout:\n---\n%s\n---", result.stdout.strip())
        if result.stderr:
            logger.debug("rclone stderr:\n---\n%s\n---", result.stderr.strip())
        return True

    except subprocess.CalledProcessError as e:
        error_details = f"rclone command failed with exit code {e.returncode}.\nCommand: {' '.join(command)}\nStderr:\n{e.stderr}\nStdout:\n{e.stdout}"
        logger.error(f"Upload FAILED (rclone).\n{error_details}")
        send_notification("Upload FAILED (rclone)", error_details)
        return False
    except Exception as e:
        logger.exception("An unexpected error occurred during rclone upload.")
        send_notification("Upload FAILED (rclone - unexpected)", f"{error_msg}\nCheck logs.")
        return False


# --- Backup Functions (Keep as is) ---
def create_backup(db_url, backup_dir=BACKUP_DB_DIR):
    """Create a PostgreSQL backup"""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"render_backup_{timestamp}.dump"
    logger.info(f"Attempting PostgreSQL backup to {backup_file}...")
    try:
        pg_dump_cmd = ["pg_dump", "-Fc", "-v", "-d", db_url, "-f", str(backup_file)]
        logger.info(f"Executing pg_dump command...")
        result = subprocess.run(pg_dump_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        logger.info(f"✓ Backup created successfully: {backup_file}")
        logger.debug("pg_dump output:\n---\n%s\n---", result.stderr.strip())
        return str(backup_file)
    except subprocess.CalledProcessError as e:
        error_details = f"pg_dump Error:\nReturn Code: {e.returncode}\nStderr: {e.stderr}\nStdout: {e.stdout}"
        logger.error(f"Backup FAILED.\n{error_details}")
        send_notification("Backup FAILED", error_details)
        return None
    except FileNotFoundError:
        error_msg = "Error: 'pg_dump' command not found. Make sure PostgreSQL client tools are installed and in your PATH."
        logger.error(error_msg)
        send_notification("Backup FAILED", error_msg)
        return None
    except Exception as e:
        logger.exception("An unexpected error occurred during backup.")
        send_notification("Backup FAILED (Unexpected)", f"Error: {e}\nCheck logs.")
        return None

# --- Restore Functions (Keep as is) ---
def restore_backup(db_url, backup_file):
    """Restore a PostgreSQL backup"""
    backup_file_path = Path(backup_file)
    logger.info(f"Attempting to restore from backup: {backup_file_path}")
    if not backup_file_path.is_file():
         err_msg = f"Restore FAILED: Backup file not found at {backup_file}"
         logger.error(err_msg)
         send_notification("Restore FAILED", err_msg)
         return False
    try:
        pg_restore_cmd = [
            "pg_restore", "--clean", "--if-exists", "--no-owner",
            "--no-privileges", "-v", "-d", db_url, str(backup_file_path)
        ]
        logger.info(f"Executing pg_restore command...")
        result = subprocess.run(pg_restore_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        msg = f"✓ Successfully restored {backup_file_path.name}" # Simplified msg
        logger.info(msg)
        logger.debug("pg_restore output:\n---\n%s\n---", result.stdout.strip())
        send_notification("Restore Successful", msg)
        return True
    except subprocess.CalledProcessError as e:
        error_details = f"pg_restore Error:\nReturn Code: {e.returncode}\nStderr: {e.stderr}\nStdout: {e.stdout}"
        logger.error(f"Restore FAILED.\n{error_details}")
        send_notification("Restore FAILED", error_details)
        return False
    except FileNotFoundError:
        error_msg = "Error: 'pg_restore' command not found. Make sure PostgreSQL client tools are installed and in your PATH."
        logger.error(error_msg)
        send_notification("Restore FAILED", error_msg)
        return False
    except Exception as e:
        logger.exception("An unexpected error occurred during restore.")
        send_notification("Restore FAILED (Unexpected)", f"Error: {e}\nCheck logs.")
        return False

# --- Email Notification (Keep as is) ---
def send_notification(subject, body):
    """Send email notification"""
    sender = os.getenv('EMAIL_FROM')
    recipient = os.getenv('EMAIL_TO')
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port_str = os.getenv('SMTP_PORT', '587')
    smtp_user = os.getenv('SMTP_USERNAME')
    smtp_pass = os.getenv('SMTP_PASSWORD')

    if not all([sender, recipient, smtp_server, smtp_user, smtp_pass]):
        logger.warning("Email notification skipped: Missing required environment variables.")
        return
    try:
        smtp_port = int(smtp_port_str)
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"[Backup Tool] {subject}"
        msg.attach(MIMEText(str(body), 'plain'))
        logger.info(f"Attempting to send email notification to {recipient} via {smtp_server}:{smtp_port}...")
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("✓ Notification email sent successfully.")
    except smtplib.SMTPAuthenticationError:
        logger.error("Failed to send email: SMTP Authentication failed. Check credentials.")
    except Exception as e:
        logger.exception("Failed to send email due to an unexpected error.")

# --- Main Function ---
def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL Backup/Restore Tool with Cloud Upload via rclone",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("action", choices=["backup", "restore", "list"], help="Action to perform")
    parser.add_argument("--db-url", help="Database URL (REQUIRED for restore, optional for backup overriding .env)")
    parser.add_argument("--backup-file", help="Specific backup file to restore (full path or relative to backup-dir)")
    parser.add_argument("--backup-dir", default=str(BACKUP_DB_DIR), help="Directory to store/find local backups")
    parser.add_argument("--upload", action="store_true", help="Upload backup using rclone after creation")
    parser.add_argument("--rclone-remote", help="Name of the configured rclone remote (overrides RCLONE_REMOTE_NAME in .env)")
    parser.add_argument("--rclone-target-dir", default=DEFAULT_RCLONE_TARGET_DIR, help=f"Target directory name on the rclone remote (default: '{DEFAULT_RCLONE_TARGET_DIR}')")
    args = parser.parse_args()

    logger.info(f"Starting backup tool with action: {args.action}")

    # --- Get Required Config ---
    # DB URL is checked specific to action below
    db_url = args.db_url or os.getenv("RENDER_DB_URL")
    rclone_remote_name = args.rclone_remote or os.getenv('RCLONE_REMOTE_NAME')
    rclone_target_dir = args.rclone_target_dir # Uses arg default or provided value
    local_backup_dir = Path(args.backup_dir)

    # --- Action: backup ---
    if args.action == "backup":
        if not db_url:
            logger.error("No database URL provided for backup. Use --db-url or set RENDER_DB_URL in .env")
            return
        # Check rclone config only if upload requested
        if args.upload and not rclone_remote_name:
            logger.error("Upload requested but no rclone remote name provided. Use --rclone-remote or set RCLONE_REMOTE_NAME in .env")
            return

        backup_file_path = create_backup(db_url, local_backup_dir)
        if backup_file_path and args.upload:
            logger.info(f"Backup successful, proceeding with upload via rclone...")
            success = upload_backup_with_rclone(
                backup_file_path,
                rclone_remote_name,
                rclone_target_dir
            )
            if success:
                try:
                    file_size_mb = Path(backup_file_path).stat().st_size / 1024 / 1024
                    size_str = f"{file_size_mb:.2f} MB"
                except FileNotFoundError:
                    logger.warning(f"Could not get size of backup file {backup_file_path} after upload.")
                    size_str = "Unknown size"
                notification_body = (
                    f"Backup created and uploaded via rclone.\n\n"
                    f"File: {os.path.basename(backup_file_path)}\n"
                    f"Size: {size_str}\n"
                    f"Remote: {rclone_remote_name}\n"
                    f"Directory: {rclone_target_dir}"
                )
                send_notification("Backup Successful & Uploaded (rclone)", notification_body)
        elif backup_file_path:
             logger.info("Backup created locally, upload not requested.")
        else:
             logger.error("Backup creation failed. See previous logs.")

    # --- Action: restore ---
    elif args.action == "restore":
        # --db-url is REQUIRED for restore
        if not db_url:
             logger.error("Restore action requires a destination database URL. Use --db-url or set RENDER_DB_URL.")
             return

        target_backup_path = None # Full path to the final backup file to restore

        if args.backup_file:
            # User specified a file
            provided_path = Path(args.backup_file)
            if provided_path.is_absolute():
                 target_backup_path = str(provided_path)
            else:
                 target_backup_path = str(local_backup_dir / args.backup_file)
            logger.info(f"Attempting to restore specific backup: {target_backup_path}")
            if not Path(target_backup_path).is_file():
                 logger.error(f"Specified backup file not found: {target_backup_path}")
                 send_notification("Restore Failed", f"Specified backup file not found: {target_backup_path}")
                 return

        else:
            # No specific file given, check local first
            logger.info(f"No specific backup file provided. Checking local directory: {local_backup_dir}")
            latest_local_backup = None
            if local_backup_dir.exists() and local_backup_dir.is_dir():
                backups = sorted(
                    [f for f in local_backup_dir.iterdir() if f.is_file() and f.name.endswith(".dump")],
                    key=lambda f: f.stat().st_mtime,
                    reverse=True
                )
                if backups:
                    latest_local_backup = backups[0]
                    logger.info(f"Found latest local backup: {latest_local_backup.name}")
                    try:
                        confirm = input(f"Restore this local backup? (y/N): ")
                        if confirm.lower() == 'y':
                            target_backup_path = str(latest_local_backup)
                        else:
                            logger.info("Restore cancelled by user.")
                            return
                    except EOFError: # Handle non-interactive environments
                         logger.warning("Cannot confirm restore in non-interactive mode. Aborting.")
                         return

            if not target_backup_path: # If no local found or user didn't confirm
                logger.info(f"No suitable local backup found or confirmed in '{local_backup_dir}'.")
                if not rclone_remote_name:
                     logger.error("Cannot check GDrive: No rclone remote name configured.")
                     return

                try:
                    confirm_gdrive = input(f"Try downloading latest backup from GDrive '{rclone_remote_name}:{rclone_target_dir}'? (y/N): ")
                    if confirm_gdrive.lower() == 'y':
                        downloaded_path = download_latest_from_gdrive(
                            rclone_remote_name,
                            rclone_target_dir,
                            local_backup_dir # Download to local backup dir
                        )
                        if downloaded_path:
                            target_backup_path = downloaded_path
                            logger.info(f"Will restore downloaded backup: {target_backup_path}")
                        else:
                            logger.error("Failed to find or download latest backup from GDrive.")
                            return # Exit if download failed
                    else:
                        logger.info("Restore cancelled by user.")
                        return
                except EOFError:
                     logger.warning("Cannot confirm GDrive download in non-interactive mode. Aborting.")
                     return


        # Proceed with restore if a target file was determined
        if target_backup_path:
             logger.info(f"Proceeding to restore {target_backup_path} to database specified by --db-url.")
             restore_backup(db_url, target_backup_path)
        else:
            # This should ideally not be reached if logic above is correct
             logger.error("No backup file selected or found for restore.")


    # --- Action: list ---
    elif args.action == "list":
         # (List logic remains unchanged - it only lists local files)
        logger.info(f"Listing local backups in directory: '{local_backup_dir}'")
        if local_backup_dir.exists() and local_backup_dir.is_dir():
            backups = sorted([f for f in local_backup_dir.iterdir() if f.is_file() and f.name.endswith(".dump")], key=lambda f: f.stat().st_mtime, reverse=True)
            if not backups: logger.info(f"No .dump backups found in '{local_backup_dir}'."); return
            logger.info(f"Available local backups:")
            list_output = []
            for i, backup in enumerate(backups, 1):
                try:
                     size_mb = backup.stat().st_size / 1024 / 1024
                     mtime = datetime.fromtimestamp(backup.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                     list_output.append(f"{i}. {backup.name} ({size_mb:.2f} MB, {mtime})")
                except Exception as e:
                     list_output.append(f"{i}. Error listing {backup.name}: {e}")
                     logger.warning(f"Error getting details for backup {backup.name}: {e}")
            print("\n".join(list_output))
        else:
            logger.error(f"Backup directory '{local_backup_dir}' does not exist or is not a directory.")

    logger.info(f"Backup tool action '{args.action}' finished.")

# --- Entry Point ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("An unhandled exception occurred in main execution.")
