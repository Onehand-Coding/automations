#!/usr/bin/env python3
import argparse
import json
import os
import pickle
import shutil
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

# Sibling module: resolved at runtime because the CLI runs this file as a script
# with its own directory on sys.path.
from helper import DATA_DIR, setup_logging  # pyright: ignore[reportMissingImports]

# --- Google Drive Upload Imports ---
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials  # noqa: F401
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    # Keep the names bound so type checkers agree with the availability flag.
    Request = InstalledAppFlow = build = MediaFileUpload = None
    GOOGLE_LIBS_AVAILABLE = False
# --- End Google Drive Upload Imports ---


# Load environment variables
load_dotenv()

# --- Directory constants ---
CREDENTIALS_DIR = DATA_DIR / "backup-tool"
BACKUP_DB_DIR = CREDENTIALS_DIR / "db"
DEFAULT_RCLONE_TARGET_DIR = "DB_Backups"


def normalize_rclone_remote(name):
    """Strip the trailing colon rclone prints in `rclone listremotes`.

    Without this, 'remote:' plus the target path becomes 'remote::DB_Backups',
    which silently uploads into a folder literally named ':DB_Backups'.
    """
    return name.rstrip(":") if name else name


# GDrive constants
GDRIVE_TOKEN_FILE = CREDENTIALS_DIR / "token.pickle"  # Assume token in data dir
GDRIVE_CREDS_FILE = CREDENTIALS_DIR / "credentials.json"  # Assume creds in data dir
GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

logger = setup_logging(log_file="backup_tool.log")


# --- Rclone Helper Functions ---
def check_rclone():
    """Checks if rclone exists and returns path or None."""
    rclone_path = shutil.which("rclone")
    if not rclone_path:
        error_msg = (
            "rclone command not found. Please install rclone and ensure it's in your system's PATH."
        )
        logger.error(error_msg)
        return None
    return rclone_path


def download_latest_from_rclone(rclone_remote_name, remote_dir_name, local_dest_dir):
    """Finds and downloads the latest .dump file from rclone remote."""
    logger.info(
        f"Checking rclone remote '{rclone_remote_name}:{remote_dir_name}' for latest backup..."
    )
    rclone_path = check_rclone()
    if not rclone_path:
        send_notification("rclone Restore Failed", "rclone not found, cannot check remote.")
        return None

    remote_path = f"{rclone_remote_name}:{remote_dir_name}"
    command = [rclone_path, "lsjson", remote_path, "--files-only"]

    try:
        logger.debug(f"Executing rclone command: {' '.join(command)}")
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding="utf-8"
        )
        files_json = json.loads(result.stdout)

        dump_files = [f for f in files_json if f.get("Name", "").endswith(".dump")]

        if not dump_files:
            logger.warning(f"No .dump files found in rclone remote directory '{remote_path}'.")
            return None

        # Find the latest file based on ModTime
        latest_file_meta = max(dump_files, key=lambda f: f.get("ModTime", ""))
        latest_filename = latest_file_meta.get("Name")
        remote_file_path = f"{remote_path}/{latest_filename}"
        local_file_path = Path(local_dest_dir) / latest_filename

        logger.info(
            f"Latest rclone remote backup found: '{latest_filename}'. Attempting download..."
        )

        download_command = [
            rclone_path,
            "copyto",
            "--progress",
            "--verbose",
            remote_file_path,
            str(local_file_path),
        ]
        logger.info(f"Executing rclone download command: {' '.join(download_command)}")
        dl_result = subprocess.run(
            download_command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        logger.info(
            f"✓ Successfully downloaded '{latest_filename}' to '{local_dest_dir}' via rclone."
        )
        logger.debug("rclone download stdout:\n---\n%s\n---", dl_result.stdout.strip())
        if dl_result.stderr:
            logger.debug("rclone download stderr:\n---\n%s\n---", dl_result.stderr.strip())
        return str(local_file_path)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse rclone lsjson output: {e}")
        send_notification("rclone Restore Failed", "Failed to parse rclone output.")
        return None
    except subprocess.CalledProcessError as e:
        error_details = f"rclone command failed (lsjson or copyto) with exit code {e.returncode}.\nStderr:\n{e.stderr}\nStdout:\n{e.stdout}"
        logger.error(f"rclone download/check failed.\n{error_details}")
        send_notification("rclone Restore Failed", error_details)
        return None
    except Exception as e:
        logger.exception("An unexpected error occurred during rclone latest backup check/download.")
        send_notification("rclone Restore Failed (Unexpected)", f"Error: {e}\nCheck logs.")
        return None


# --- Upload Function using rclone ---
def upload_backup_with_rclone(
    local_file_path, rclone_remote_name, target_dir_name=DEFAULT_RCLONE_TARGET_DIR
):
    """Uploads the backup file to a specific directory on an rclone remote."""
    local_file_path = Path(local_file_path)
    logger.info(
        f"Attempting upload via rclone to remote '{rclone_remote_name}', directory '{target_dir_name}'..."
    )

    rclone_path = check_rclone()  # Use helper
    if not rclone_path:
        send_notification("Upload FAILED (rclone)", "rclone command not found.")
        return False

    destination = f"{rclone_remote_name}:{target_dir_name}/"
    command = [
        rclone_path,
        "copyto",
        "--drive-skip-gdocs",  # Assuming GDrive backend might be used
        "--progress",
        "--verbose",
        str(local_file_path),
        destination + local_file_path.name,
    ]

    logger.info(f"Executing rclone command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding="utf-8"
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
        send_notification("Upload FAILED (rclone - unexpected)", f"Error: {e}\nCheck logs.")
        return False


# --- Upload Function using Google Drive API ---
def upload_to_gdrive(local_file_path, target_filename=None):
    """Uploads the backup file directly to Google Drive root."""
    if not GOOGLE_LIBS_AVAILABLE:
        logger.error("Google API libraries not installed. Cannot upload to Google Drive.")
        logger.error(
            "Install them using: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )
        send_notification("Upload FAILED (GDrive)", "Google API libraries missing.")
        return False

    local_file_path = Path(local_file_path)
    if not local_file_path.is_file():
        logger.error(f"GDrive Upload Failed: Local file not found at {local_file_path}")
        send_notification("Upload FAILED (GDrive)", f"Local file not found: {local_file_path.name}")
        return False

    logger.info(f"Attempting upload via Google Drive API for file: {local_file_path.name}")
    creds = None
    if Request is None or InstalledAppFlow is None:
        logger.error("GDrive upload requires google-auth and google-auth-oauthlib installed.")
        return False

    # --- Credential Handling (from gdrive_uploader.py) ---
    if GDRIVE_TOKEN_FILE.exists():
        try:
            with open(GDRIVE_TOKEN_FILE, "rb") as token:
                # pi-lens-ignore: python-insecure-deserialization
                creds = pickle.load(
                    token
                )  # nosemgrep: python.lang.security.deserialization.pickle.avoid-pickle
            logger.debug("Loaded GDrive credentials from token file.")
        except Exception as e:
            logger.warning(
                f"Could not load token file '{GDRIVE_TOKEN_FILE}': {e}. Will try to refresh/re-auth."
            )
            creds = None  # Ensure creds is None if load fails

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("GDrive credentials expired, attempting refresh...")
                creds.refresh(Request())
                logger.info("✓ GDrive credentials refreshed.")
            except Exception as e:
                logger.error(f"Failed to refresh GDrive token: {e}")
                creds = None  # Force re-auth if refresh fails
        # Only attempt interactive flow if creds are still missing
        if not creds:
            if not GDRIVE_CREDS_FILE.is_file():
                logger.error(
                    f"GDrive authentication required, but credentials file not found at '{GDRIVE_CREDS_FILE}'"
                )
                send_notification("Upload FAILED (GDrive)", "GDrive credentials.json missing.")
                return False
            try:
                logger.info(
                    f"GDrive credentials not found or invalid. Starting authentication flow using '{GDRIVE_CREDS_FILE}'."
                )
                # Create the flow using the client secrets file
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(GDRIVE_CREDS_FILE),
                    GDRIVE_SCOPES,
                    redirect_uri="urn:ietf:wg:oauth:2.0:oob",
                )  # Use Out-Of-Band flow suitable for CLI

                # Generate the authorization URL
                auth_url, _ = flow.authorization_url(
                    access_type="offline", include_granted_scopes="true"
                )

                print("\n--- Google Drive Authentication Needed ---")
                print("Please visit this URL on any device with a browser:")
                print(auth_url)
                # Prompt user for the authorization code interactively
                code = input("Enter the authorization code obtained from the URL: ").strip()

                if not code:
                    logger.error(
                        "No authorization code entered. Cannot proceed with GDrive upload."
                    )
                    send_notification(
                        "Upload FAILED (GDrive)",
                        "GDrive authentication cancelled (no code).",
                    )
                    return False

                # Exchange the authorization code for credentials
                flow.fetch_token(code=code)
                creds = flow.credentials
                logger.info("✓ Successfully obtained GDrive credentials.")
            except FileNotFoundError:
                logger.error(f"GDrive credentials file not found at: {GDRIVE_CREDS_FILE}")
                send_notification("Upload FAILED (GDrive)", "credentials.json not found.")
                return False
            except Exception as e:
                logger.error(f"An error occurred during GDrive authentication flow: {e}")
                send_notification("Upload FAILED (GDrive)", f"Authentication error: {e}")
                return False

        # Save the credentials for the next run
        try:
            with open(GDRIVE_TOKEN_FILE, "wb") as token:
                pickle.dump(
                    creds, token
                )  # nosemgrep: python.lang.security.deserialization.pickle.avoid-pickle
            logger.info(f"GDrive credentials saved to '{GDRIVE_TOKEN_FILE}'")
        except Exception as e:
            logger.error(f"Failed to save GDrive token to '{GDRIVE_TOKEN_FILE}': {e}")
            # Don't fail the upload just because saving token failed

    # --- End Credential Handling ---

    try:
        # Build the Drive v3 service
        if build is None or MediaFileUpload is None:
            logger.error("GDrive upload requires google-api-python-client installed.")
            return False
        logger.info("Building Google Drive service...")
        service = build(
            "drive",
            "v3",
            credentials=creds,
            static_discovery=False,  # pyright: ignore[reportCallIssue]
        )  # static_discovery=False can help sometimes

        # Prepare file metadata and media body
        file_metadata = {"name": target_filename if target_filename else local_file_path.name}
        logger.info(f"Preparing to upload '{file_metadata['name']}'...")
        media = MediaFileUpload(str(local_file_path), resumable=True)

        # Execute the upload
        logger.info("Starting GDrive file upload...")
        file = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id,name,webViewLink",  # Request fields needed for confirmation
            )
            .execute()
        )

        file_id = file.get("id")
        file_name = file.get("name")
        file_link = file.get("webViewLink")
        logger.info("✓ Google Drive upload successful!")
        logger.info(f"  File Name: {file_name}")
        logger.info(f"  File ID: {file_id}")
        logger.info(f"  View Link: {file_link}")
        return True  # Indicate success

    except Exception as e:
        logger.exception("An unexpected error occurred during Google Drive upload")
        send_notification("Upload FAILED (GDrive - unexpected)", f"Error: {e}\nCheck logs.")
        return False


# --- PostgreSQL Client Resolution ---
# Docker image used when pg_dump/pg_restore are not installed locally.
# Its major version must be >= the server's, so keep it up to date.
PG_CLIENT_IMAGE = "postgres:17-alpine"
CONTAINER_BACKUP_MOUNT = "/pg_backup"


def _docker_ready():
    """Return True when a usable Docker daemon is reachable."""
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _pg_client(tool, host_dir=None):
    """Resolve a PostgreSQL client tool to a command prefix and path mapper.

    Prefers the locally installed binary and falls back to the pinned Docker
    image, so backups work without installing PostgreSQL client packages.
    """
    if shutil.which(tool):
        return [tool], Path
    if not _docker_ready():
        raise FileNotFoundError(
            f"'{tool}' is not installed and Docker is unavailable. Install the PostgreSQL "
            f"client tools (e.g. 'sudo dnf install postgresql') or start Docker."
        )
    logger.info(f"'{tool}' not found on PATH; using '{PG_CLIENT_IMAGE}' via Docker.")
    # Host networking keeps localhost DB URLs and VPN/DNS resolution working.
    prefix = ["docker", "run", "--rm", "-i", "--network", "host"]
    if host_dir is not None:
        prefix += ["-v", f"{host_dir}:{CONTAINER_BACKUP_MOUNT}:ro"]
    prefix += [PG_CLIENT_IMAGE, tool]

    def to_container_path(path):
        return Path(CONTAINER_BACKUP_MOUNT) / Path(path).name

    return prefix, to_container_path


def _decode(output):
    """Decode subprocess output that may be bytes or str."""
    if not output:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


# --- Backup Functions ---
def create_backup(db_url, backup_dir=BACKUP_DB_DIR):
    """Create a PostgreSQL backup"""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"db_backup_{timestamp}.dump"
    logger.info(f"Attempting PostgreSQL backup to {backup_file}...")
    try:
        pg_dump_prefix, _ = _pg_client("pg_dump")
        pg_dump_cmd = [*pg_dump_prefix, "-Fc", "-v", "-d", db_url]
        logger.info("Executing pg_dump command...")
        # Dump to stdout so the file is always owned by the current user, even
        # when pg_dump runs inside a container.
        with open(backup_file, "wb") as dump_file:
            result = subprocess.run(
                pg_dump_cmd,
                check=True,
                stdout=dump_file,
                stderr=subprocess.PIPE,
            )
        backup_file.chmod(0o600)
        logger.info(f"✓ Backup created successfully: {backup_file}")
        # pg_dump's verbose output goes to stderr
        if result.stderr:
            logger.debug("pg_dump output:\n---\n%s\n---", _decode(result.stderr).strip())
        return str(backup_file)
    except subprocess.CalledProcessError as e:
        error_details = f"pg_dump Error:\nReturn Code: {e.returncode}\nStderr: {_decode(e.stderr)}"
        logger.error(f"Backup FAILED.\n{error_details}")
        # Never leave a truncated dump behind: it looks like a valid backup.
        backup_file.unlink(missing_ok=True)
        send_notification("Backup FAILED", error_details)
        return None
    except FileNotFoundError as e:
        error_msg = f"Error: {e}"
        logger.error(error_msg)
        backup_file.unlink(missing_ok=True)
        send_notification("Backup FAILED", error_msg)
        return None
    except Exception as e:
        logger.exception("An unexpected error occurred during backup.")
        backup_file.unlink(missing_ok=True)
        send_notification("Backup FAILED (Unexpected)", f"Error: {e}\nCheck logs.")
        return None


# --- Restore Functions ---
def restore_backup(db_url, backup_file):
    """Restore a PostgreSQL backup"""
    backup_file_path = Path(backup_file).resolve()
    logger.info(f"Attempting to restore from backup: {backup_file_path}")
    if not backup_file_path.is_file():
        err_msg = f"Restore FAILED: Backup file not found at {backup_file}"
        logger.error(err_msg)
        send_notification("Restore FAILED", err_msg)
        return False
    try:
        # Mount the backup's directory read-only when pg_restore runs in Docker.
        pg_restore_prefix, to_client_path = _pg_client(
            "pg_restore", host_dir=backup_file_path.parent
        )
        pg_restore_cmd = [
            *pg_restore_prefix,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "-v",
            "-d",
            db_url,
            str(to_client_path(backup_file_path)),
        ]
        logger.info("Executing pg_restore command...")
        # pg_restore verbose output goes to stdout
        result = subprocess.run(
            pg_restore_cmd, check=True, capture_output=True, text=True, encoding="utf-8"
        )
        msg = f"✓ Successfully restored {backup_file_path.name}"  # Simplified msg
        logger.info(msg)
        # Log pg_restore's verbose output (usually on stdout)
        if result.stdout:
            logger.debug("pg_restore output:\n---\n%s\n---", result.stdout.strip())
        # Also log stderr just in case
        if result.stderr:
            logger.debug("pg_restore stderr:\n---\n%s\n---", result.stderr.strip())
        send_notification("Restore Successful", msg)
        return True
    except subprocess.CalledProcessError as e:
        error_details = f"pg_restore Error:\nReturn Code: {e.returncode}\nStderr: {e.stderr}\nStdout: {e.stdout}"
        logger.error(f"Restore FAILED.\n{error_details}")
        send_notification("Restore FAILED", error_details)
        return False
    except FileNotFoundError as e:
        error_msg = f"Error: {e}"
        logger.error(error_msg)
        send_notification("Restore FAILED", error_msg)
        return False
    except Exception as e:
        logger.exception("An unexpected error occurred during restore.")
        send_notification("Restore FAILED (Unexpected)", f"Error: {e}\nCheck logs.")
        return False


# --- Email Notification ---
def send_notification(subject, body):
    """Send email notification"""
    sender = os.getenv("EMAIL_FROM")
    recipient = os.getenv("EMAIL_TO")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port_str = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not (sender and recipient and smtp_server and smtp_user and smtp_pass):
        logger.warning("Email notification skipped: Missing required environment variables.")
        return
    try:
        smtp_port = int(smtp_port_str)
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = f"[PG Backup Tool] {subject}"  # Added PG prefix
        # Ensure body is string
        msg.attach(MIMEText(str(body), "plain", "utf-8"))  # Added encoding
        logger.info(
            f"Attempting to send email notification to {recipient} via {smtp_server}:{smtp_port}..."
        )
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("✓ Notification email sent successfully.")
    except smtplib.SMTPAuthenticationError:
        logger.error("Failed to send email: SMTP Authentication failed. Check credentials.")
    except Exception as e:
        # Log without exc_info: this runs inside another handler, so a traceback
        # would drag in the unrelated failure that triggered the notification.
        logger.error("Failed to send email: %s", e)


# --- Main Function ---
def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL Backup/Restore Tool with Cloud Upload Options",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("action", choices=["backup", "restore", "list"], help="Action to perform")
    parser.add_argument(
        "--db-url",
        help="Database connection string/URL (REQUIRED for restore, overrides DB_URL in .env for backup)",
    )
    parser.add_argument(
        "--backup-file",
        help="Specific backup file to restore (full path or relative to backup-dir)",
    )
    parser.add_argument(
        "--backup-dir",
        default=str(BACKUP_DB_DIR),
        help="Directory to store/find local backups",
    )
    # Upload options
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload backup to the cloud after creation",
    )
    parser.add_argument(
        "--upload-method",
        choices=["rclone", "gdrive"],
        default="rclone",
        help="Cloud upload method to use (default: rclone)",
    )
    # rclone specific options
    parser.add_argument(
        "--rclone-remote",
        help="Name of the configured rclone remote (overrides RCLONE_REMOTE_NAME in .env)",
    )
    parser.add_argument(
        "--rclone-target-dir",
        default=DEFAULT_RCLONE_TARGET_DIR,
        help=f"Target directory name on the rclone remote (default: '{DEFAULT_RCLONE_TARGET_DIR}')",
    )
    # GDrive specific options (currently uploads to root, could add folder option later)
    # parser.add_argument("--gdrive-target-dir", help="Target directory ID or path on Google Drive (optional)") # Example for future

    args = parser.parse_args()

    logger.info(f"Starting backup tool with action: {args.action}")

    # --- Get Required Config ---
    db_url = args.db_url or os.getenv("DB_URL")
    local_backup_dir = Path(args.backup_dir)

    # --- Action: backup ---
    if args.action == "backup":
        if not db_url:
            logger.error(
                "Backup action requires a database URL. Use --db-url or set DB_URL in .env."
            )
            return 1

        backup_file_path = create_backup(db_url, local_backup_dir)

        if backup_file_path and args.upload:
            logger.info(f"Backup successful, proceeding with upload via '{args.upload_method}'...")

            upload_successful = False
            upload_details = {}

            if args.upload_method == "rclone":
                # --- Rclone Upload ---
                rclone_remote_name = normalize_rclone_remote(
                    args.rclone_remote or os.getenv("RCLONE_REMOTE_NAME")
                )
                if not rclone_remote_name:
                    logger.error(
                        "rclone upload requested but no remote name provided. Use --rclone-remote or set RCLONE_REMOTE_NAME in .env."
                    )
                else:
                    upload_successful = upload_backup_with_rclone(
                        backup_file_path,
                        rclone_remote_name,
                        args.rclone_target_dir,  # Use the arg value directly
                    )
                    upload_details = {
                        "Method": "rclone",
                        "Remote": rclone_remote_name,
                        "Directory": args.rclone_target_dir,
                    }

            elif args.upload_method == "gdrive":
                # --- Google Drive Upload ---
                if not GOOGLE_LIBS_AVAILABLE:
                    logger.error(
                        "Google Drive upload requested, but required libraries are missing."
                    )
                    logger.error(
                        "Please install: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
                    )
                else:
                    upload_successful = upload_to_gdrive(backup_file_path)
                    upload_details = {
                        "Method": "Google Drive API"
                    }  # Can add File ID later if needed

            else:
                # Should not happen due to argparse choices
                logger.error(f"Invalid upload method specified: {args.upload_method}")

            # --- Post-Upload Notification ---
            if upload_successful:
                try:
                    file_size_mb = Path(backup_file_path).stat().st_size / (1024 * 1024)
                    size_str = f"{file_size_mb:.2f} MB"
                except FileNotFoundError:
                    logger.warning(
                        f"Could not get size of backup file {backup_file_path} after upload."
                    )
                    size_str = "Unknown size"

                notification_subject = (
                    f"Backup Successful & Uploaded ({upload_details.get('Method', 'Unknown')})"
                )
                notification_body = (
                    f"Backup created and uploaded.\n\n"
                    f"File: {os.path.basename(backup_file_path)}\n"
                    f"Size: {size_str}\n"
                    f"Method: {upload_details.get('Method', 'N/A')}\n"
                )
                if "Remote" in upload_details:
                    notification_body += f"Remote: {upload_details['Remote']}\n"
                if "Directory" in upload_details:
                    notification_body += f"Directory: {upload_details['Directory']}\n"

                send_notification(notification_subject, notification_body)
            else:
                logger.warning(
                    f"Upload via {args.upload_method} failed or was skipped. Check previous logs."
                )
                # Send notification about backup success but upload failure/skip
                send_notification(
                    f"Backup Successful (Upload FAILED/Skipped - {args.upload_method})",
                    f"Backup created locally: {os.path.basename(backup_file_path)}\nUpload via {args.upload_method} did not complete successfully.",
                )
                return 1

        elif backup_file_path:
            logger.info("Backup created locally, upload not requested.")
            # Optionally send notification about local backup success
            # send_notification("Backup Successful (Local Only)", f"Backup created: {os.path.basename(backup_file_path)}")
        else:
            logger.error("Backup creation failed. See previous logs.")
            return 1

    # --- Action: restore ---
    elif args.action == "restore":
        # DB URL is REQUIRED for restore
        if not db_url:
            logger.error(
                "Restore action requires a destination database URL. Use --db-url or set DB_URL."
            )
            return 1

        target_backup_path = None  # Full path to the final backup file to restore

        if args.backup_file:
            # User specified a file
            provided_path = Path(args.backup_file)
            if provided_path.is_absolute():
                target_backup_path = str(provided_path)
            else:
                target_backup_path = str(local_backup_dir / args.backup_file)
            logger.info(f"Attempting to restore specific backup file: {target_backup_path}")
            if not Path(target_backup_path).is_file():
                logger.error(f"Specified backup file not found: {target_backup_path}")
                send_notification(
                    "Restore Failed",
                    f"Specified backup file not found: {target_backup_path}",
                )
                return 1
        else:
            # No specific file given, check local first
            logger.info(
                f"No specific backup file provided. Checking local directory: {local_backup_dir}"
            )
            latest_local_backup = None
            if local_backup_dir.exists() and local_backup_dir.is_dir():
                backups = sorted(
                    [
                        f
                        for f in local_backup_dir.iterdir()
                        if f.is_file() and f.name.endswith(".dump")
                    ],
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
                if backups:
                    latest_local_backup = backups[0]
                    logger.info(f"Found latest local backup: {latest_local_backup.name}")
                    try:
                        confirm = (
                            input(
                                f"Restore this local backup '{latest_local_backup.name}'? (y/N): "
                            )
                            .lower()
                            .strip()
                        )
                        if confirm == "y":
                            target_backup_path = str(latest_local_backup)
                        else:
                            logger.info("Local restore cancelled by user.")
                            # Don't return yet, might try remote download
                    except EOFError:  # Handle non-interactive environments
                        logger.warning(
                            "Cannot confirm local restore in non-interactive mode. Checking remote..."
                        )
                        latest_local_backup = None  # Treat as not confirmed

            if not target_backup_path:  # If no local found or user didn't confirm local
                if not latest_local_backup:  # Only log this if local wasn't even found
                    logger.info(f"No suitable local backup found in '{local_backup_dir}'.")

                # Check if rclone remote is configured for potential download
                rclone_remote_name = normalize_rclone_remote(
                    args.rclone_remote or os.getenv("RCLONE_REMOTE_NAME")
                )
                if not rclone_remote_name:
                    logger.info("No rclone remote configured, cannot check for remote backups.")
                else:
                    try:
                        rclone_target_dir = args.rclone_target_dir  # Use the arg value directly
                        confirm_remote = (
                            input(
                                f"Try downloading latest backup from rclone remote '{rclone_remote_name}:{rclone_target_dir}'? (y/N): "
                            )
                            .lower()
                            .strip()
                        )
                        if confirm_remote == "y":
                            downloaded_path = download_latest_from_rclone(
                                rclone_remote_name,
                                rclone_target_dir,
                                local_backup_dir,  # Download to local backup dir
                            )
                            if downloaded_path:
                                target_backup_path = downloaded_path
                                logger.info(f"Will restore downloaded backup: {target_backup_path}")
                            else:
                                logger.error(
                                    "Failed to find or download latest backup from rclone remote."
                                )
                                return 1  # Exit if download failed
                        else:
                            logger.info("Remote download cancelled by user.")
                            # Exit if user cancelled remote check and local wasn't chosen
                            if not target_backup_path:
                                return 1

                    except EOFError:
                        logger.warning(
                            "Cannot confirm remote download in non-interactive mode. Aborting."
                        )
                        return 1

        # Proceed with restore if a target file was determined
        if target_backup_path:
            logger.info(
                f"Proceeding to restore {Path(target_backup_path).name} to database specified by --db-url."
            )
            return 0 if restore_backup(db_url, target_backup_path) else 1
        else:
            logger.error("No backup file selected, found, or downloaded for restore.")
            return 1

    # --- Action: list ---
    elif args.action == "list":
        logger.info(f"Listing local backups in directory: '{local_backup_dir}'")
        if local_backup_dir.exists() and local_backup_dir.is_dir():
            backups = sorted(
                [f for f in local_backup_dir.iterdir() if f.is_file() and f.name.endswith(".dump")],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if not backups:
                print(f"\nNo .dump backups found locally in '{local_backup_dir}'.")
                logger.info(f"No .dump backups found locally in '{local_backup_dir}'.")
                # Optionally add listing from rclone remote here if needed
                return 0

            print(f"\nAvailable local backups in '{local_backup_dir}':")
            list_output = []
            for i, backup in enumerate(backups, 1):
                try:
                    size_mb = backup.stat().st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(backup.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    list_output.append(f"  {i}. {backup.name} ({size_mb:.2f} MB, {mtime})")
                except Exception as e:
                    list_output.append(f"  {i}. Error listing {backup.name}: {e}")
                    logger.warning(f"Error getting details for backup {backup.name}: {e}")
            print("\n".join(list_output))
            # TODO: Add optional listing from rclone/gdrive if desired
        else:
            logger.error(
                f"Backup directory '{local_backup_dir}' does not exist or is not a directory."
            )
            print(f"\nError: Backup directory '{local_backup_dir}' not found.")
            return 1

    logger.info(f"Backup tool action '{args.action}' finished.")
    return 0


# --- Entry Point ---
if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
    except Exception as e:
        # Log the exception with traceback before exiting
        logger.exception("An unhandled exception occurred in main execution.")
        # Optionally print a simpler message to stderr for the user
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)  # Exit with a non-zero code to indicate failure
