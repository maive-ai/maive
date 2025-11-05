#!/usr/bin/env python3
"""
Script to download audio and transcript files from a single row in Excel/CSV files.
Creates organized folders and names files with UUIDs.
"""

import argparse
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pandas as pd


def download_file(url, output_path):
    """Download a file using wget."""
    try:
        subprocess.run(
            ["wget", "-O", output_path, url], check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {url}: {e}")
        return False


def detect_file_type(file_path):
    """Detect actual file type using the 'file' command."""
    try:
        result = subprocess.run(
            ["file", "--mime-type", "-b", file_path],
            check=True,
            capture_output=True,
            text=True,
        )
        mime_type = result.stdout.strip()
        return mime_type
    except subprocess.CalledProcessError as e:
        print(f"Error detecting file type: {e}")
        return None


def get_proper_extension(mime_type):
    """Map MIME type to proper file extension."""
    ext_map = {
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-m4a": ".m4a",
        "audio/mp4": ".m4a",
        "audio/aac": ".aac",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
    }
    return ext_map.get(mime_type, ".audio")


def convert_to_mp3(input_path, mp3_path, bitrate="64k"):
    """Convert any audio file to MP3 using ffmpeg with specified bitrate."""
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-b:a", bitrate, "-y", mp3_path],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting {input_path} to MP3: {e}")
        return False


def process_single_row(input_file, row_number, base_output_dir):
    """Process a single row from an Excel or CSV file and download audio/transcript files."""
    # Determine file type and read accordingly
    file_path = Path(input_file)

    if file_path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(input_file)
    elif file_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_file)
    else:
        print(f"Unsupported file type: {file_path.suffix}")
        return

    # Create output folder named after the input file (without extension)
    folder_name = file_path.stem
    output_dir = Path(base_output_dir) / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {input_file}")
    print(f"Output directory: {output_dir}")

    # Validate row number (subtract 1 because headers are included in row count)
    # Row number 1 = headers, Row number 2 = first data row (index 0), etc.
    if row_number < 2:
        print("Error: Row number must be 2 or greater (row 1 is headers)")
        return

    data_row_index = (
        row_number - 2
    )  # Convert to 0-based index (accounting for header row)

    if data_row_index >= len(df):
        print(
            f"Error: Row number {row_number} is out of range. File has {len(df) + 1} rows (including header)"
        )
        return

    print(f"Processing row {row_number} (data row index {data_row_index})")

    # Find columns containing audio and transcript URLs
    audio_col = None
    transcript_col = None

    for col in df.columns:
        col_lower = str(col).lower()
        if "audio" in col_lower and "url" in col_lower:
            audio_col = col
        elif "transcript" in col_lower and "url" in col_lower:
            transcript_col = col

    if audio_col is None or transcript_col is None:
        print(f"Available columns: {df.columns.tolist()}")
        print("Error: Could not find audio and transcript URL columns")
        return

    print(f"Using columns: audio='{audio_col}', transcript='{transcript_col}'")

    # Get the specific row
    row = df.iloc[data_row_index]
    audio_url = row[audio_col]
    transcript_url = row[transcript_col]

    # Check if URLs are missing
    if pd.isna(audio_url) or pd.isna(transcript_url):
        print(f"Error: Row {row_number} has missing URL(s)")
        print(f"  Audio URL: {audio_url}")
        print(f"  Transcript URL: {transcript_url}")
        return

    print(f"\nAudio URL: {audio_url}")
    print(f"Transcript URL: {transcript_url}")

    # Generate UUID for this pair
    file_uuid = str(uuid.uuid4())
    print(f"Generated UUID: {file_uuid}")

    # Download to temporary file first to detect actual type
    temp_audio = output_dir / f"{file_uuid}.tmp"
    transcript_output = output_dir / f"{file_uuid}.txt"

    audio_success = False
    transcript_success = False
    final_audio_path = None

    # Download audio file
    print("\nDownloading audio file...")
    if download_file(audio_url, str(temp_audio)):
        print("Audio downloaded to temporary file")

        # Detect the actual file type
        mime_type = detect_file_type(str(temp_audio))
        print(f"Detected file type: {mime_type}")

        # Get proper extension based on actual file type
        proper_ext = get_proper_extension(mime_type) if mime_type else ".audio"
        final_audio_path = output_dir / f"{file_uuid}{proper_ext}"

        # Rename temp file to proper extension
        temp_audio.rename(final_audio_path)
        audio_success = True
        print(f"Audio saved: {final_audio_path.absolute()}")
    else:
        print("Failed to download audio file")

    # Sleep so we don't get kicked off Rilla
    time.sleep(3)

    # Download transcript file
    print("\nDownloading transcript file...")
    if download_file(transcript_url, str(transcript_output)):
        transcript_success = True
        print(f"Transcript saved: {transcript_output.absolute()}")
    else:
        print("Failed to download transcript file")

    # Print summary
    print(f"\n{'=' * 80}")
    print("Summary:")
    print(f"  Row number: {row_number}")
    print(f"  UUID: {file_uuid}")
    print(f"  Audio download: {'SUCCESS' if audio_success else 'FAILED'}")
    if audio_success and final_audio_path:
        print(f"  Audio file: {final_audio_path.name}")
    print(f"  Transcript download: {'SUCCESS' if transcript_success else 'FAILED'}")
    if transcript_success:
        print(f"  Transcript file: {transcript_output.name}")
    print(f"{'=' * 80}")


def main():
    parser = argparse.ArgumentParser(
        description="Download audio and transcript files from a single row in Excel/CSV files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_audio_transcripts.py data.xlsx 2
  python download_audio_transcripts.py data.csv 5

Note: Row numbers include the header row. Row 1 is headers, row 2 is the first data row, etc.
        """,
    )
    parser.add_argument("file", help="Excel or CSV file to process")
    parser.add_argument(
        "row_number", type=int, help="Row number to process (includes header row)"
    )

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    # Use relative path from script location
    script_dir = Path(__file__).parent
    base_output_dir = script_dir / "output"

    process_single_row(args.file, args.row_number, base_output_dir)


if __name__ == "__main__":
    main()
