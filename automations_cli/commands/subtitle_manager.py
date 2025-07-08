import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Optional

import pysrt

try:
    from helper.configs import setup_logging
except ImportError:
    from .helper.configs import setup_logging

logger = setup_logging(log_file="subtitle_manager.log")


def sync_subtitle(video_path: Path, unsynced_srt: Path, output_srt: Path):
    """
    Automatically synchronizes a subtitle file with a video file using ffsubsync.

    Args:
        video_path: Path to the video file.
        unsynced_srt: Path to the out-of-sync .srt file.
        output_srt: Path for the new, automatically synced .srt file.
    """
    if not shutil.which("ffsubsync"):
        errmsg = "❌ ffsubsync is not installed or not in your PATH. Please install it with 'pip install ffsubsync'."
        logger.error(errmsg)
        print(errmsg, file=sys.stderr)
        return

    logger.info(
        f"Automatically syncing '{unsynced_srt.name}' with '{video_path.name}'."
    )

    command = [
        "ffsubsync",
        str(video_path),
        "-i",
        str(unsynced_srt),
        "-o",
        str(output_srt),
    ]

    logger.debug(f"Executing command: {' '.join(command)}")
    print("▶️  Running ffsubsync... (This may take a minute)")

    try:
        # Using capture_output to hide the verbose output of ffsubsync unless there's an error
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding="utf-8"
        )
        logger.info(result.stdout)
        success_msg = (
            f"✅ Successfully created synced subtitle file: '{output_srt.name}'"
        )
        logger.info(success_msg)
        print(success_msg)

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to sync subtitles with ffsubsync.")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        print(f"❌ Error syncing subtitles. Check logs for details.", file=sys.stderr)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        print(f"❌ An unexpected error occurred. Check logs.", file=sys.stderr)


def shift_subtitle(input_srt: Path, output_srt: Path, offset_seconds: float):
    """
    Creates a new, time-shifted subtitle file using the pysrt library.

    Args:
        input_srt: Path to the original .srt file.
        output_srt: Path for the new, shifted .srt file.
        offset_seconds: The time offset in seconds (e.g., -13.0 or 5.5).
    """
    logger.info(f"Shifting subtitle '{input_srt.name}' by {offset_seconds} seconds.")

    try:
        # 1. Open and parse the original SRT file using pysrt.open()
        #
        #    THE FIX IS HERE:
        #    We changed from the incorrect srt.parse(f.read()) to the
        #    correct pysrt.open(input_srt)
        #
        subs = pysrt.open(input_srt, encoding="utf-8")

        # 2. Apply the offset to each subtitle entry
        subs.shift(seconds=offset_seconds)  # pysrt has a built-in method for this!

        # 3. Save the modified subtitles to the new file
        subs.save(output_srt, encoding="utf-8")

        success_msg = (
            f"✅ Successfully created shifted subtitle file: '{output_srt.name}'"
        )
        logger.info(success_msg)
        print(success_msg)

    except Exception as e:
        logger.error(f"Failed to shift subtitles: {e}")
        print(f"❌ Error shifting subtitles. Check logs.", file=sys.stderr)


def embed_subtitle(
    video_path: Path,
    subtitle_path: Path,
    output_path: Path,
    offset: float,
    hard_sub: bool,
):
    """
    Embeds a subtitle file into a video file using ffmpeg.
    """
    # This function remains unchanged
    if not shutil.which("ffmpeg"):
        # ... (rest of the embed function is the same)
        return

    logger.info(f"Embedding subtitles for video: {video_path.name}")
    command = ["ffmpeg", "-i", str(video_path)]

    if hard_sub:
        logger.info("Mode: Hardsub (burning subtitles onto video)")
        command.extend(
            [
                "-vf",
                f"subtitles='{subtitle_path}'",
                "-c:a",
                "copy",
                "-c:v",
                "libx264",
                "-crf",
                "23",
                "-preset",
                "fast",
                str(output_path),
            ]
        )
    else:
        logger.info("Mode: Softsub (embedding as a selectable track)")
        command.extend(
            [
                "-itsoffset",
                str(offset),
                "-i",
                str(subtitle_path),
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-c:s",
                "mov_text",
                "-metadata:s:s:0",
                "language=eng",
                str(output_path),
            ]
        )

    logger.debug(f"Executing command: {' '.join(command)}")
    print(f"▶️  Running ffmpeg...")

    try:
        subprocess.run(command, check=True)
        success_msg = f"✅ Successfully created '{output_path.name}'"
        logger.info(success_msg)
        print(success_msg)
    except Exception as e:
        logger.error(f"Failed to embed subtitles: {e}")
        print(f"❌ Error embedding subtitles. Check logs.", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subtitle management tool.")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # --- Sync command ---
    sync_parser = subparsers.add_parser(
        "sync", help="Automatically sync a subtitle file with a video."
    )
    sync_parser.add_argument("video_path", help="Path to the video file.")
    sync_parser.add_argument(
        "input_srt", help="Path to the original (unsynced) .srt file."
    )
    sync_parser.add_argument("output_srt", help="Path for the new, synced .srt file.")

    # --- Shift command ---
    shift_parser = subparsers.add_parser(
        "shift", help="Create a new, time-shifted subtitle file."
    )
    shift_parser.add_argument("input_srt", help="Path to the original .srt file.")
    shift_parser.add_argument("output_srt", help="Path for the new, shifted .srt file.")
    shift_parser.add_argument(
        "--offset",
        type=float,
        required=True,
        help="Time offset in seconds (e.g., -13.0).",
    )

    # --- Embed command ---
    embed_parser = subparsers.add_parser("embed", help="Embed subtitles into a video.")
    embed_parser.add_argument("video_path", help="Path to the input video file.")
    embed_parser.add_argument("subtitle_path", help="Path to the .srt subtitle file.")
    embed_parser.add_argument("output_path", help="Path for the new output video file.")
    embed_parser.add_argument(
        "--offset",
        type=float,
        default=0.0,
        help="Softsub synchronization offset in seconds.",
    )
    embed_parser.add_argument(
        "--hard",
        action="store_true",
        help="Burn subtitles permanently into the video (re-encodes).",
    )

    args = parser.parse_args()

    if args.action == "sync":
        sync_subtitle(
            Path(args.video_path), Path(args.input_srt), Path(args.output_srt)
        )
    elif args.action == "shift":
        shift_subtitle(Path(args.input_srt), Path(args.output_srt), args.offset)
    elif args.action == "embed":
        embed_subtitle(
            Path(args.video_path),
            Path(args.subtitle_path),
            Path(args.output_path),
            args.offset,
            args.hard,
        )
