#!/usr/bin/env python3
"""
Google Photos Takeout Processor - Final Working Version
"""

import os
import json
import shutil
from datetime import datetime
import argparse
import piexif
import platform
from typing import Optional, Dict, Any, Tuple
import subprocess
from pathlib import Path
import logging
from tqdm import tqdm

class GooglePhotosMetadataRestorer:
    def __init__(self, root_dir: str, remove_json: bool = True, dry_run: bool = False, quiet: bool = False):
        # Initialize logger first
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File handler (always enabled)
        log_path = os.path.join(root_dir, 'photos_restore.log')
        fh = logging.FileHandler(log_path)
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # Console handler (only if not quiet)
        if not quiet:
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        self.root_dir = os.path.abspath(root_dir)
        self.video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.3gp'}
        self.supported_image_extensions = {'.jpg', '.jpeg'}
        self.total_processed = 0
        self.skipped_files = 0
        self.videos_moved = 0
        self.json_files_removed = 0
        self.remove_json = remove_json
        self.dry_run = dry_run
        self.quiet = quiet
        
        # Check ffmpeg after logger is setup
        self.ffmpeg_available = self._check_ffmpeg()

        if dry_run:
            self.logger.info("DRY RUN MODE - No files will be modified")

    def _is_video_file(self, filename: str) -> bool:
        """Check if file is a video based on extension"""
        return os.path.splitext(filename.lower())[1] in self.video_extensions

    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available for video metadata writing"""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         check=True)
            return True
        except (FileNotFoundError, subprocess.SubprocessError):
            self.logger.warning("ffmpeg not found. Video metadata won't be modified.")
            return False

    def process_directory(self):
        """Main method to process the directory tree"""
        self.logger.info(f"Processing directory: {self.root_dir}")
        self.logger.info(f"Platform: {platform.system()} {platform.release()}")
        
        if self.ffmpeg_available:
            self.logger.info("ffmpeg detected - video metadata will be processed")
        
        self.logger.info(
            f"JSON files will {'be removed' if self.remove_json else 'NOT be removed'} "
            f"after processing{' (dry run)' if self.dry_run else ''}"
        )

        # First scan to count files for progress bars
        total_files = 0
        self.logger.info("Scanning directory structure...")
        for _, _, files in os.walk(self.root_dir):
            total_files += len(files)

        # Main processing with progress bars
        with tqdm(total=total_files, desc="Overall Progress", unit="file", dynamic_ncols=True, disable=self.quiet) as pbar:
            for root, _, files in os.walk(self.root_dir):
                # Check if this directory has any video files
                has_videos = any(self._is_video_file(f) for f in files)
                
                if has_videos:
                    videos_dir = os.path.join(root, 'Videos')
                    if not self.dry_run and not os.path.exists(videos_dir):
                        os.makedirs(videos_dir)

                # Process files in current directory with progress
                dir_progress = tqdm(files, desc=f"Processing {os.path.basename(root)}", 
                                  leave=False, dynamic_ncols=True, disable=self.quiet)
                for file in dir_progress:
                    file_path = os.path.join(root, file)
                    try:
                        if self._is_video_file(file):
                            if has_videos:
                                new_path = self._move_video_file(file_path, videos_dir)
                                self.videos_moved += 1
                                if self.ffmpeg_available:
                                    self._process_video_metadata(new_path)
                        elif file.lower().endswith('.json'):
                            media_path = self._process_json_file(file_path)
                            if media_path and self.remove_json and not self.dry_run:
                                self._remove_json_file(file_path)
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path}: {str(e)}")
                        self.skipped_files += 1
                    finally:
                        pbar.update(1)
                        dir_progress.set_postfix({
                            'processed': self.total_processed,
                            'videos': self.videos_moved,
                            'skipped': self.skipped_files
                        })

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print processing summary"""
        self.logger.info("\nProcessing complete!")
        self.logger.info(f"Total files processed: {self.total_processed}")
        self.logger.info(f"Videos moved: {self.videos_moved}")
        self.logger.info(f"JSON files removed: {self.json_files_removed}")
        self.logger.info(f"Skipped files: {self.skipped_files}")

        # Always show summary in console if quiet mode
        if self.quiet:
            print("\nProcessing complete!")
            print(f"Total files processed: {self.total_processed}")
            print(f"Videos moved: {self.videos_moved}")
            print(f"JSON files removed: {self.json_files_removed}")
            print(f"Skipped files: {self.skipped_files}")
            print(f"Detailed logs saved to: {os.path.join(self.root_dir, 'photos_restore.log')}")

    def _move_video_file(self, src_path: str, videos_dir: str) -> str:
        """Move video file to Videos directory with conflict resolution"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would move video: {src_path} -> {videos_dir}")
            return src_path

        filename = os.path.basename(src_path)
        dest_path = os.path.join(videos_dir, filename)
        
        # Handle duplicate filenames
        counter = 1
        while os.path.exists(dest_path):
            name, ext = os.path.splitext(filename)
            dest_path = os.path.join(videos_dir, f"{name}_{counter}{ext}")
            counter += 1

        try:
            shutil.move(src_path, dest_path)
            self.videos_moved += 1
            self.logger.info(f"Moved video: {src_path} -> {dest_path}")
            return dest_path
        except OSError as e:
            self.logger.error(f"Failed to move video {src_path}: {str(e)}")
            raise

    def _process_json_file(self, json_path: str) -> Optional[str]:
        """Process a JSON metadata file and return corresponding media path if found"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.error(f"Invalid JSON file: {json_path} - {str(e)}")
            self.skipped_files += 1
            return None

        # Find corresponding media file
        media_path = self._find_media_file(json_path)
        if not media_path:
            return None

        # Process based on file type
        ext = os.path.splitext(media_path.lower())[1]
        if ext in self.supported_image_extensions:
            self._process_image_file(media_path, metadata)
        self.total_processed += 1

        return media_path

    def _find_media_file(self, json_path: str) -> Optional[str]:
        """Find the media file corresponding to a JSON file with robust pattern matching"""
        json_filename = os.path.basename(json_path)
        dir_path = os.path.dirname(json_path)
        
        # Handle all possible JSON suffix patterns
        base_patterns = [
            json_filename.replace('.json', ''),
            json_filename.replace('.supplemental.json', ''),
            json_filename.replace('.supplem.json', ''),
            json_filename.split('.')[0]  # For files like "1c93bcdc6fc626e6e5f14afb2249f8fa.0.jpg.supplem.json"
        ]
        
        # Try all possible media extensions
        possible_extensions = self.supported_image_extensions.union(self.video_extensions)
        
        # Check directory files against all possible patterns
        for file in os.listdir(dir_path):
            file_lower = file.lower()
            
            # Skip JSON files
            if file_lower.endswith(('.json', '.supplem.json', '.supplemental.json')):
                continue
                
            # Check against all base patterns
            for pattern in base_patterns:
                pattern_lower = pattern.lower()
                
                # Case 1: Exact match (without extension)
                if file_lower.startswith(pattern_lower) and any(file_lower.endswith(ext) for ext in possible_extensions):
                    return os.path.join(dir_path, file)
                    
                # Case 2: Match with additional numbering (common in Google Photos)
                if (file_lower.startswith(pattern_lower.split('.')[0]) and 
                    any(file_lower.endswith(ext) for ext in possible_extensions)):
                    return os.path.join(dir_path, file)
        
        # If not found, try removing all metadata suffixes
        clean_base = json_filename.split('.')[0]
        for file in os.listdir(dir_path):
            file_lower = file.lower()
            if (file_lower.startswith(clean_base.lower()) and 
                any(file_lower.endswith(ext) for ext in possible_extensions)):
                return os.path.join(dir_path, file)
        
        self.logger.warning(f"No matching media file found for {json_path}")
        self.skipped_files += 1
        return None

    def _process_image_file(self, image_path: str, metadata: Dict[str, Any]):
        """Restore metadata to an image file"""
        try:
            # Extract relevant metadata from JSON
            exif_data = self._create_exif_data(metadata)
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would update metadata for {image_path}")
                return

            if image_path.lower().endswith(('.jpg', '.jpeg')):
                self._update_jpeg_exif(image_path, exif_data)
            
            # Update file timestamp
            self._update_file_timestamp(image_path, metadata)
            self.logger.info(f"Updated metadata for {image_path}")

        except Exception as e:
            self.logger.error(f"Failed to process {image_path}: {str(e)}")
            self.skipped_files += 1

    def _create_exif_data(self, metadata: Dict[str, Any]) -> Dict[int, Any]:
        """Create EXIF data dictionary from Google Photos metadata"""
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        
        # Add timestamp
        if 'photoTakenTime' in metadata and 'timestamp' in metadata['photoTakenTime']:
            timestamp = metadata['photoTakenTime']['timestamp']
            try:
                dt = datetime.fromtimestamp(int(timestamp))
                exif_dict["0th"][piexif.ImageIFD.DateTime] = dt.strftime("%Y:%m:%d %H:%M:%S")
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt.strftime("%Y:%m:%d %H:%M:%S")
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = dt.strftime("%Y:%m:%d %H:%M:%S")
            except (ValueError, OSError):
                pass

        # Add GPS data if available
        if 'geoData' in metadata:
            self._add_gps_data(exif_dict, metadata['geoData'])

        # Add description if available
        if 'description' in metadata and metadata['description']:
            try:
                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = metadata['description'][:199]
            except Exception:
                pass

        return exif_dict

    def _add_gps_data(self, exif_dict: Dict[int, Any], geo_data: Dict[str, Any]):
        """Add GPS data to EXIF dictionary"""
        if 'latitude' not in geo_data or 'longitude' not in geo_data:
            return

        try:
            lat = float(geo_data['latitude'])
            lon = float(geo_data['longitude'])
            
            gps_ifd = {
                piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
                piexif.GPSIFD.GPSLatitudeRef: 'N' if lat >= 0 else 'S',
                piexif.GPSIFD.GPSLatitude: self._decimal_to_dms(abs(lat)),
                piexif.GPSIFD.GPSLongitudeRef: 'E' if lon >= 0 else 'W',
                piexif.GPSIFD.GPSLongitude: self._decimal_to_dms(abs(lon)),
            }
            
            if 'altitude' in geo_data:
                alt = float(geo_data['altitude'])
                gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 0 if alt >= 0 else 1
                gps_ifd[piexif.GPSIFD.GPSAltitude] = (int(abs(alt) * 100), 100)
            
            exif_dict["GPS"] = gps_ifd
        except (ValueError, KeyError):
            pass

    def _decimal_to_dms(self, decimal: float) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        """Convert decimal degrees to degrees, minutes, seconds"""
        degrees = int(decimal)
        remainder = (decimal - degrees) * 60
        minutes = int(remainder)
        seconds = int((remainder - minutes) * 60 * 100)
        return ((degrees, 1), (minutes, 1), (seconds, 100))

    def _update_jpeg_exif(self, image_path: str, exif_dict: Dict[int, Any]):
        """Update EXIF data for JPEG files"""
        try:
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
        except Exception as e:
            self.logger.error(f"Failed to update EXIF for {image_path}: {str(e)}")
            raise

    def _process_video_metadata(self, video_path: str):
        """Process video metadata from corresponding JSON file"""
        json_path = self._find_json_for_media(video_path)
        if not json_path:
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.error(f"Invalid JSON file: {json_path} - {str(e)}")
            return

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would update video metadata for {video_path}")
            return

        # Update video metadata using ffmpeg
        self._update_video_metadata(video_path, metadata)
        self.total_processed += 1

    def _update_video_metadata(self, video_path: str, metadata: Dict[str, Any]):
        """Update video metadata using ffmpeg"""
        creation_time = self._get_creation_time(metadata)
        if not creation_time:
            return

        try:
            # Create temporary file
            temp_path = video_path + '.tmp'
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite without asking
                '-i', video_path,
                '-metadata', f'creation_time={creation_time}',
                '-codec', 'copy',  # Don't re-encode
                '-movflags', 'use_metadata_tags',
                '-f', 'mp4',
                temp_path
            ]
            
            # Run ffmpeg
            subprocess.run(cmd, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         check=True)
            
            # Replace original file
            os.replace(temp_path, video_path)
            
            # Update file system timestamp
            self._update_file_timestamp(video_path, metadata)
            
            self.logger.info(f"Updated video metadata for {video_path}")
            
        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to update video metadata for {video_path}: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def _get_creation_time(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Get creation time in ISO format for ffmpeg"""
        if 'photoTakenTime' in metadata and 'timestamp' in metadata['photoTakenTime']:
            try:
                timestamp = int(metadata['photoTakenTime']['timestamp'])
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except (ValueError, OSError):
                pass
        return None

    def _find_json_for_media(self, media_path: str) -> Optional[str]:
        """Find JSON file for a given media file"""
        base_path = os.path.splitext(media_path)[0]
        json_path = base_path + '.json'
        
        if os.path.exists(json_path):
            return json_path
        
        # Case-insensitive search
        parent_dir = os.path.dirname(media_path)
        media_stem = Path(media_path).stem.lower()
        
        for file in os.listdir(parent_dir):
            if file.lower().endswith('.json'):
                file_stem = Path(file).stem.lower()
                if file_stem == media_stem:
                    return os.path.join(parent_dir, file)
        
        self.logger.warning(f"No matching JSON file found for {media_path}")
        return None

    def _update_file_timestamp(self, file_path: str, metadata: Dict[str, Any]):
        """Update file modification time from metadata"""
        if self.dry_run:
            return

        if 'photoTakenTime' in metadata and 'timestamp' in metadata['photoTakenTime']:
            try:
                timestamp = int(metadata['photoTakenTime']['timestamp'])
                os.utime(file_path, (timestamp, timestamp))
            except (ValueError, OSError):
                pass

    def _remove_json_file(self, json_path: str):
        """Safely remove a JSON file after processing"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would remove JSON file: {json_path}")
            return

        try:
            os.remove(json_path)
            self.json_files_removed += 1
            self.logger.info(f"Removed JSON file: {json_path}")
        except OSError as e:
            self.logger.error(f"Failed to remove JSON file {json_path}: {str(e)}")
            self.skipped_files += 1

def main():
    parser = argparse.ArgumentParser(
        description="Google Photos Takeout Processor\n"
                    "Restores metadata to media files, organizes videos, and cleans up JSON files",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("directory", help="Directory containing Google Photos Takeout files")
    parser.add_argument("--keep-json", action="store_true", help="Keep JSON files after processing")
    parser.add_argument("--dry-run", action="store_true", help="Simulate processing without making changes")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output (progress bars still visible)")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found - {args.directory}")
        return
    
    processor = GooglePhotosMetadataRestorer(
        args.directory,
        remove_json=not args.keep_json,
        dry_run=args.dry_run,
        quiet=args.quiet
    )
    processor.process_directory()

if __name__ == "__main__":
    main()