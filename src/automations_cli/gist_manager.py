#!/usr/bin/env python3
import re
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

try:
    from helper.configs import setup_logging
except ImportError:
    from .helper.configs import setup_logging

logger = setup_logging(log_file="gist_uploader.log")


def get_gists(token: str) -> list:
    """Fetch user's gists from GitHub API."""
    url = "https://api.github.com/gists"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        gists = response.json()
        # Sort by creation date, newest first
        return sorted(
            gists,
            key=lambda x: datetime.strptime(x["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
            reverse=True,
        )
    except requests.RequestException as e:
        logger.error(f"Failed to fetch gists: {e}")
        print(f"❌ Failed to fetch gists: {e}", file=sys.stderr)
        sys.exit(1)


def find_gist_by_filename(token: str, filenames: list[str], description: str) -> list:
    """Find gists containing any of the specified filenames and optionally matching description."""
    gists = get_gists(token)
    matching_gists = []
    for gist in gists:
        gist_files = list(gist["files"].keys())
        if any(filename in gist_files for filename in filenames):
            if not description or (
                gist["description"]
                and description.lower() in gist["description"].lower()
            ):
                matching_gists.append(gist)
    return matching_gists


def find_gist_by_id(token: str, gist_id: str) -> dict:
    """Find a gist by its ID."""
    if not re.match(r"^[0-9a-f]{32}$", gist_id):
        logger.error(f"Invalid gist ID format: {gist_id}")
        print(f"❌ Invalid gist ID format: {gist_id}", file=sys.stderr)
        sys.exit(1)
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def list_gists(token: str):
    """Lists user's existing gists."""
    gists = get_gists(token)
    if not gists:
        print("No gists found.")
        logger.info("No gists found.")
        return

    print("Your GitHub Gists:")
    for gist in gists:
        gist_id = gist["id"]
        description = gist["description"] or "No description"
        filenames = ", ".join(gist["files"].keys())
        url = gist["html_url"]
        created_at = datetime.strptime(
            gist["created_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).strftime("%Y-%m-%d %H:%M:%S")
        print(f"ID: {gist_id}")
        print(f"Description: {description}")
        print(f"Files: {filenames}")
        print(f"URL: {url}")
        print(f"Created: {created_at}")
        print("-" * 50)
    logger.info(f"Listed {len(gists)} gists.")


def upload_gist(
    file_paths: list[Path],
    description: str,
    public: bool,
    token: str,
    non_interactive: bool = False,
) -> str:
    """
    Uploads multiple files as a new GitHub Gist, checking for duplicates first.

    Args:
        file_paths: List of paths to the files to upload.
        description: Description for the gist.
        public: If True, create a public gist; otherwise, create a secret gist.
        token: GitHub API token.
        non_interactive: If True, skip prompting and create new gist.
    """
    # Validate file existence and read content
    files_content = {}
    filenames = []
    for file_path in file_paths:
        if not file_path.is_file():
            errmsg = f"❌ File '{file_path}' does not exist."
            logger.error(errmsg)
            print(errmsg, file=sys.stderr)
            sys.exit(1)
        try:
            with file_path.open("r", encoding="utf-8") as f:
                files_content[file_path.name] = {"content": f.read()}
            filenames.append(file_path.name)
        except Exception as e:
            errmsg = f"❌ Failed to read file '{file_path}': {e}"
            logger.error(errmsg)
            print(errmsg, file=sys.stderr)
            sys.exit(1)

    # Check for existing gists
    if not non_interactive:
        matching_gists = find_gist_by_filename(token, filenames, description)
        if matching_gists:
            print("Existing gists found with matching files:")
            for gist in matching_gists:
                gist_id = gist["id"]
                desc = gist["description"] or "No description"
                files = ", ".join(gist["files"].keys())
                url = gist["html_url"]
                created_at = datetime.strptime(
                    gist["created_at"], "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%Y-%m-%d %H:%M:%S")
                print(f"ID: {gist_id}")
                print(f"Description: {desc}")
                print(f"Files: {files}")
                print(f"URL: {url}")
                print(f"Created: {created_at}")
                print("-" * 50)
            try:
                choice = input(
                    "Enter gist ID to update, 'n' for new gist, or 'c' to cancel: "
                ).strip()
                if choice.lower() == "c":
                    print("Operation cancelled.")
                    sys.exit(0)
                if choice.lower() != "n" and re.match(r"^[0-9a-f]{32}$", choice):
                    return update_gist(file_paths, choice, description, token)
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                sys.exit(0)

    # Prepare API request
    url = "https://api.github.com/gists"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "public": public,
        "files": files_content,
        "description": description
        or f"Uploaded {', '.join(file_path.name for file_path in file_paths)} via automations CLI",
    }

    # Make API request
    logger.info(
        f"Uploading gist for files: {', '.join(str(file_path) for file_path in file_paths)}"
    )
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        gist_url = response.json().get("html_url")
        success_msg = f"✅ Successfully created gist: {gist_url}"
        logger.debug(success_msg)
        print(success_msg)
        return gist_url
    except requests.RequestException as e:
        errmsg = f"❌ Failed to create gist: {e}"
        logger.error(errmsg)
        print(errmsg, file=sys.stderr)
        sys.exit(1)


def update_gist(
    file_paths: list[Path], update: str, description: str, token: str
) -> str:
    """
    Updates an existing gist by filename or gist ID.

    Args:
        file_paths: List of paths to the files to update (empty for description-only updates).
        update: Filename or gist ID to identify the gist.
        description: New description (if provided, else reuse existing).
        token: GitHub API token.
    """
    # Get gist by filename or ID
    gist = None
    if re.match(r"^[0-9a-f]{32}$", update):
        gist = find_gist_by_id(token, update)
    else:
        matching_gists = find_gist_by_filename(token, [update], description)
        gist = matching_gists[0] if matching_gists else None

    if not gist:
        errmsg = f"❌ No gist found with filename or ID '{update}'."
        logger.error(errmsg)
        print(errmsg, file=sys.stderr)
        sys.exit(1)

    gist_id = gist["id"]
    existing_description = (
        gist["description"]
        or f"Uploaded {', '.join(gist['files'].keys())} via automations CLI"
    )

    # Prepare files for update
    files_content = {}
    if file_paths:
        for file_path in file_paths:
            if not file_path.is_file():
                errmsg = f"❌ File '{file_path}' does not exist."
                logger.error(errmsg)
                print(errmsg, file=sys.stderr)
                sys.exit(1)
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    files_content[file_path.name] = {"content": f.read()}
            except Exception as e:
                errmsg = f"❌ Failed to read file '{file_path}': {e}"
                logger.error(errmsg)
                print(errmsg, file=sys.stderr)
                sys.exit(1)

    # Prepare API request
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Build payload - only include files if we have files to update
    payload = {
        "description": description or existing_description,
    }

    # Only include files in payload if we have files to update
    # This prevents accidentally deleting all files when doing description-only updates
    if files_content:
        payload["files"] = files_content

    # Make API request
    logger.info(
        f"Updating gist {gist_id} for files: {', '.join(str(file_path) for file_path in file_paths) if file_paths else 'description only'}"
    )
    try:
        response = requests.patch(url, json=payload, headers=headers)
        response.raise_for_status()
        gist_url = response.json().get("html_url")
        success_msg = f"✅ Successfully updated gist: {gist_url}"
        logger.debug(success_msg)
        print(success_msg)
        return gist_url
    except requests.RequestException as e:
        errmsg = f"❌ Failed to update gist: {e}"
        logger.error(errmsg)
        print(errmsg, file=sys.stderr)
        sys.exit(1)


def delete_gist(token: str, gist_identifier: str) -> bool:
    """
    Deletes a GitHub Gist by its ID or filename.

    Args:
        token: GitHub API token.
        gist_identifier: Gist ID or filename to identify the gist to delete.

    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    # Find gist by ID or filename
    gist = None
    if re.match(r"^[0-9a-f]{32}$", gist_identifier):
        gist = find_gist_by_id(token, gist_identifier)
    else:
        matching_gists = find_gist_by_filename(token, [gist_identifier], "")
        gist = matching_gists[0] if matching_gists else None

    if not gist:
        errmsg = f"❌ No gist found with filename or ID '{gist_identifier}'."
        logger.error(errmsg)
        print(errmsg, file=sys.stderr)
        sys.exit(1)

    gist_id = gist["id"]
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    logger.info(f"Deleting gist {gist_id}")
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        success_msg = f"✅ Successfully deleted gist: {gist_id}"
        logger.debug(success_msg)
        print(success_msg)
        return True
    except requests.RequestException as e:
        errmsg = f"❌ Failed to delete gist: {e}"
        logger.error(errmsg)
        print(errmsg, file=sys.stderr)
        sys.exit(1)


def download_gist(token: str, gist_id_or_url: str, output_dir: str = None):
    """Download a gist by ID or URL and save its files locally."""
    # Extract gist ID from URL if needed
    match = re.search(r"([0-9a-f]{32})", gist_id_or_url)
    if not match:
        print(f"❌ Invalid gist ID or URL: {gist_id_or_url}", file=sys.stderr)
        sys.exit(1)
    gist_id = match.group(1)

    gist = find_gist_by_id(token, gist_id)
    if not gist:
        print(f"❌ Gist not found: {gist_id}", file=sys.stderr)
        sys.exit(1)

    # Determine output directory
    if output_dir is None:
        output_dir = f"gist-{gist_id}"
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Download each file
    for filename, fileinfo in gist["files"].items():
        raw_url = fileinfo["raw_url"]
        file_content = requests.get(raw_url).text
        (out_path / filename).write_text(file_content, encoding="utf-8")
        print(f"Downloaded: {filename}")

    print(f"✅ Gist {gist_id} downloaded to {out_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage GitHub Gists.")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Upload subcommand
    upload_parser = subparsers.add_parser("upload", help="Upload files as a new gist.")
    upload_parser.add_argument(
        "file_paths", nargs="+", help="Paths to the files to upload as a gist."
    )
    upload_parser.add_argument(
        "--description", "-d", default="", help="Description for the gist."
    )
    upload_parser.add_argument(
        "--public", action="store_true", help="Create a public gist (default: secret)."
    )
    upload_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip prompting and create new gist.",
    )

    # Update subcommand
    update_parser = subparsers.add_parser(
        "update", help="Update an existing gist by filename or ID."
    )
    update_parser.add_argument(
        "file_paths",
        nargs="*",
        help="Paths to the files to update (optional for description-only updates).",
    )
    update_parser.add_argument(
        "--update",
        required=True,
        help="Filename or gist ID to identify the gist to update.",
    )
    update_parser.add_argument(
        "--description",
        "-d",
        default="",
        help="New description for the gist (uses existing if not provided).",
    )

    # List subcommand
    subparsers.add_parser("list", help="List existing gists.")

    # Delete subcommand
    delete_parser = subparsers.add_parser(
        "delete", help="Delete a gist by filename or ID."
    )
    delete_parser.add_argument(
        "gist_identifier",
        help="Gist ID or filename to identify the gist to delete.",
    )

    # Download subcommand
    download_parser = subparsers.add_parser(
        "download", help="Download a gist by ID or URL."
    )
    download_parser.add_argument(
        "gist_id_or_url", help="Gist ID or full gist URL to download."
    )
    download_parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save the gist files (default: ./gist-<id>).",
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        token_path = Path.home() / ".gist"
        if token_path.exists():
            with token_path.open("r", encoding="utf-8") as f:
                token = f.read().strip()
        else:
            errmsg = "❌ GITHUB_TOKEN not found in .env or ~/.gist file."
            logger.error(errmsg)
            print(errmsg, file=sys.stderr)
            sys.exit(1)

    if args.action == "upload":
        upload_gist(
            [Path(p) for p in args.file_paths],
            args.description,
            args.public,
            token,
            args.non_interactive,
        )
    elif args.action == "update":
        update_gist(
            [Path(p) for p in args.file_paths], args.update, args.description, token
        )
    elif args.action == "list":
        list_gists(token)
    elif args.action == "delete":
        delete_gist(token, args.gist_identifier)
    elif args.action == "download":
        download_gist(token, args.gist_id_or_url, args.output_dir)
