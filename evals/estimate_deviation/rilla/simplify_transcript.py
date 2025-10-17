#!/usr/bin/env python3
"""
Script to simplify transcript JSON files by consolidating word-level data into speaker-level segments.

This script processes JSON files containing detailed word-level transcript data and simplifies them
to reduce token count for model processing while preserving essential information.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def seconds_to_timestamp(seconds: float) -> str:
    """
    Convert seconds to HH:MM:SS timestamp format.

    Args:
        seconds: Time in seconds

    Returns:
        String in HH:MM:SS format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def simplify_transcript(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simplify transcript data by consolidating word-level information into speaker segments.

    Args:
        data: List of speaker objects with word-level data

    Returns:
        List of simplified speaker segments with consolidated transcript text and timing
    """
    simplified_segments = []

    for speaker_data in data:
        speaker = speaker_data["speaker"]
        words = speaker_data["words"]

        if not words:
            continue

        # Extract transcript text by joining all words
        transcript_text = " ".join(word["word"] for word in words)

        # Get start time from first word and end time from last word
        start_time = words[0]["start_time"]
        end_time = words[-1]["end_time"]

        # Create simplified segment with formatted timestamps
        segment = {
            "speaker": speaker,
            "transcript": transcript_text,
            "start_time": seconds_to_timestamp(start_time),
            "end_time": seconds_to_timestamp(end_time),
        }

        simplified_segments.append(segment)

    return simplified_segments


def process_file(input_file: Path, output_dir: Path) -> None:
    """
    Process a single JSON file and write the simplified version to output directory.

    Args:
        input_file: Path to the input JSON file
        output_dir: Directory to write the simplified JSON file
    """
    try:
        # Read input file
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Simplify the transcript data
        simplified_data = simplify_transcript(data)

        # Create output filename with "-simplified" suffix
        output_filename = input_file.stem + "-simplified" + input_file.suffix
        output_file = output_dir / output_filename

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write simplified data to output file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(simplified_data, f, indent=2, ensure_ascii=False)

        print(f"Processed: {input_file.name} -> {output_file.name}")

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {input_file}: {e}")
    except Exception as e:
        print(f"Error processing file {input_file}: {e}")


def main():
    """Main function to handle command line arguments and process files."""
    parser = argparse.ArgumentParser(
        description="Simplify transcript JSON files by consolidating word-level data into speaker segments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single file
  python simplify_transcript.py input.json output_dir/

  # Process all JSON files in a directory
  python simplify_transcript.py input_dir/ output_dir/
        """,
    )

    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to the input JSON file or directory containing JSON files",
    )

    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory where the simplified JSON file(s) will be written",
    )

    args = parser.parse_args()

    # Validate input path exists
    if not args.input_path.exists():
        print(f"Error: Input path '{args.input_path}' does not exist")
        return 1

    # Process based on whether input is a file or directory
    if args.input_path.is_file():
        # Validate it's a JSON file
        if args.input_path.suffix.lower() != ".json":
            print(f"Error: Input file '{args.input_path}' is not a JSON file")
            return 1

        # Process single file
        process_file(args.input_path, args.output_dir)

    elif args.input_path.is_dir():
        # Find all JSON files in the directory
        json_files = list(args.input_path.glob("*.json"))

        if not json_files:
            print(f"Error: No JSON files found in directory '{args.input_path}'")
            return 1

        print(f"Found {len(json_files)} JSON files to process")

        # Process each JSON file
        for json_file in json_files:
            process_file(json_file, args.output_dir)

        print(f"\nProcessed {len(json_files)} files successfully")
    else:
        print(
            f"Error: Input path '{args.input_path}' is neither a file nor a directory"
        )
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
