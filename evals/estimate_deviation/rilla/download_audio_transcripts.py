#!/usr/bin/env python3
"""
Script to download audio and transcript files from URLs in Excel/CSV files.
Creates organized folders and names files with UUIDs.
"""

import argparse
import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm


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


def convert_wav_to_mp3(wav_path, mp3_path, bitrate="64k"):
    """Convert WAV file to MP3 using ffmpeg."""
    try:
        subprocess.run(
            ["ffmpeg", "-i", wav_path, "-b:a", bitrate, "-y", mp3_path],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting {wav_path} to MP3: {e}")
        return False


def download_row(row_data):
    """Download audio and transcript for a single row."""
    idx, audio_url, transcript_url, file_uuid, output_dir = row_data

    # Determine audio file extension from URL (strip query parameters)
    audio_url_path = str(audio_url).split("?")[0]
    audio_ext = Path(audio_url_path).suffix or ".mp3"
    audio_output_temp = output_dir / f"{file_uuid}{audio_ext}"
    audio_output_final = output_dir / f"{file_uuid}.mp3"
    transcript_output = output_dir / f"{file_uuid}.txt"

    audio_success = False
    transcript_success = False
    audio_filename = None
    transcript_filename = None

    # Download audio file
    if download_file(audio_url, str(audio_output_temp)):
        # If it's a WAV file, convert to MP3
        if audio_ext.lower() == ".wav":
            if convert_wav_to_mp3(str(audio_output_temp), str(audio_output_final)):
                # Delete the WAV file after successful conversion
                audio_output_temp.unlink()
                audio_success = True
                audio_filename = audio_output_final.name
            else:
                # Keep WAV if conversion failed
                audio_success = True
                audio_filename = audio_output_temp.name
        else:
            audio_success = True
            audio_filename = audio_output_temp.name

    # Download transcript file
    if download_file(transcript_url, str(transcript_output)):
        transcript_success = True
        transcript_filename = transcript_output.name

    return idx, audio_success, transcript_success, audio_filename, transcript_filename


def process_file(input_file, base_output_dir, include_open=False):
    """Process an Excel or CSV file and download audio/transcript files."""
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

    # Find columns containing audio, transcript URLs, and outcome
    audio_col = None
    transcript_col = None
    outcome_col = None

    for col in df.columns:
        col_lower = str(col).lower()
        if "audio" in col_lower and "url" in col_lower:
            audio_col = col
        elif "transcript" in col_lower and "url" in col_lower:
            transcript_col = col
        elif col_lower == "outcome":
            outcome_col = col

    if audio_col is None or transcript_col is None:
        print(f"Available columns: {df.columns.tolist()}")
        print("Please specify which columns contain audio and transcript URLs")
        return

    print(f"Using columns: audio='{audio_col}', transcript='{transcript_col}'")

    if outcome_col:
        print(f"Filtering by outcome column: '{outcome_col}'")
        total_rows = len(df)

        # Filter for "Sold" and optionally "Open" outcomes
        if include_open:
            df = df[df[outcome_col].str.lower().isin(["sold", "open"])]
            filtered_rows = len(df)
            print(
                f"Found {filtered_rows} 'Sold' or 'Open' rows out of {total_rows} total rows"
            )
        else:
            df = df[df[outcome_col].str.lower() == "sold"]
            filtered_rows = len(df)
            print(f"Found {filtered_rows} 'Sold' rows out of {total_rows} total rows")
    else:
        print("Warning: No 'Outcome' column found, processing all rows")

    # Prepare download tasks and add new columns to dataframe
    df["downloaded_audio_file"] = None
    df["downloaded_transcript_file"] = None

    download_tasks = []
    for idx, row in df.iterrows():
        audio_url = row[audio_col]
        transcript_url = row[transcript_col]

        # Skip if URLs are missing
        if pd.isna(audio_url) or pd.isna(transcript_url):
            print(f"Skipping row {idx}: missing URL(s)")
            continue

        # Generate UUID for this pair
        file_uuid = str(uuid.uuid4())
        download_tasks.append((idx, audio_url, transcript_url, file_uuid, output_dir))

    # Download files in parallel (up to 10 concurrent downloads)
    print(f"\nStarting parallel downloads for {len(download_tasks)} rows...\n")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(download_row, task) for task in download_tasks]

        # Use tqdm to show progress
        with tqdm(total=len(download_tasks), desc="Downloading", unit="row") as pbar:
            for future in as_completed(futures):
                try:
                    (
                        idx,
                        audio_success,
                        transcript_success,
                        audio_filename,
                        transcript_filename,
                    ) = future.result()

                    # Update dataframe with filenames
                    if audio_filename:
                        df.at[idx, "downloaded_audio_file"] = audio_filename
                    if transcript_filename:
                        df.at[idx, "downloaded_transcript_file"] = transcript_filename

                    if not audio_success or not transcript_success:
                        tqdm.write(
                            f"Row {idx + 1}: Partial failure (audio: {audio_success}, transcript: {transcript_success})"
                        )
                except Exception as e:
                    tqdm.write(f"Error processing row: {e}")
                finally:
                    pbar.update(1)

    # Save updated dataframe to new CSV file
    csv_output_path = output_dir / f"{folder_name}_with_filenames.csv"
    df.to_csv(csv_output_path, index=False)
    print(f"\nSaved CSV with filenames to: {csv_output_path}")

    print(f"\nCompleted processing {input_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Download audio and transcript files from URLs in Excel/CSV files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_audio_transcripts.py data.xlsx
  python download_audio_transcripts.py file1.csv file2.xlsx
  python download_audio_transcripts.py --include-open data.xlsx
        """,
    )
    parser.add_argument("files", nargs="+", help="Excel or CSV files to process")
    parser.add_argument(
        "--include-open",
        action="store_true",
        help='Also download rows with "Open" outcome (default: only "Sold")',
    )

    args = parser.parse_args()

    base_output_dir = "/Users/willcray/maive/rilla_data"

    # Process each input file
    for input_file in args.files:
        if not os.path.exists(input_file):
            print(f"File not found: {input_file}")
            continue

        process_file(input_file, base_output_dir, include_open=args.include_open)
        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
