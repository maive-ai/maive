import subprocess

from src.utils.logger import logger


def convert_to_mp3(input_path: str, mp3_path: str, bitrate: str = "64k") -> bool:
    """Convert any audio file to MP3 using ffmpeg with specified bitrate.

    Args:
        input_path: Path to input audio file
        mp3_path: Path where MP3 should be saved
        bitrate: Audio bitrate (default: 64k)

    Returns:
        bool: True if conversion successful, False otherwise
    """
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-b:a", bitrate, "-y", mp3_path],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting {input_path} to MP3: {e}")
        return False


def _format_timestamp_from_seconds(seconds: float, use_hours: bool) -> str:
    """
    Convert timestamp from seconds to MM:SS or HH:MM:SS format.

    Args:
        seconds: Timestamp in seconds
        use_hours: If True, use HH:MM:SS format; if False, use MM:SS

    Returns:
        Formatted timestamp stringS
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if use_hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def simplify_rilla_transcript(rilla_transcript: list[dict]) -> dict:
    """
    Convert Rilla word-level transcript to compact format for LLM efficiency.

    Reduces token count by ~70% by:
    - Combining words into space-separated strings
    - Using parallel arrays for timestamps and confidence
    - Grouping by speaker turns
    - Using shorter timestamp format when possible

    Args:
        rilla_transcript: List of Rilla entries with format:
            [{"speaker": str, "words": [{"word": str, "start_time": float, "confidence": float}]}]

    Returns:
        Compact format dict:
            {
                "conversations": [
                    {
                        "speaker": str,
                        "words": str (space-separated),
                        "timestamps": [str] (MM:SS or HH:MM:SS),
                        "confidence": [float]
                    }
                ]
            }

    Raises:
        ValueError: If transcript is empty or malformed
    """
    if not rilla_transcript:
        raise ValueError("Transcript is empty")

    # Determine if we need hours in timestamps (any timestamp >= 1 hour)
    max_time = 0.0
    for entry in rilla_transcript:
        words = entry.get("words", [])
        if words:
            for word_obj in words:
                start_time = word_obj.get("start_time", 0)
                max_time = max(max_time, start_time)

    use_hours = max_time >= 3600

    # Group by speaker turns (consecutive entries with same speaker)
    conversations = []
    current_speaker = None
    current_words = []
    current_timestamps = []
    current_confidence = []

    for entry in rilla_transcript:
        speaker = entry.get("speaker", "Unknown")
        words = entry.get("words", [])

        if not words:
            continue

        # If speaker changed, save previous turn and start new one
        if speaker != current_speaker and current_words:
            conversations.append(
                {
                    "speaker": current_speaker,
                    "words": " ".join(current_words),
                    "timestamps": current_timestamps,
                    "confidence": current_confidence,
                }
            )
            current_words = []
            current_timestamps = []
            current_confidence = []

        current_speaker = speaker

        # Extract word, timestamp, confidence from each word object
        for word_obj in words:
            word = word_obj.get("word", "")
            start_time = word_obj.get("start_time", 0)
            conf = word_obj.get("confidence", 0.0)

            if word:  # Skip empty words
                current_words.append(word)
                current_timestamps.append(
                    _format_timestamp_from_seconds(start_time, use_hours)
                )
                current_confidence.append(round(conf, 2))

    # Don't forget the last turn
    if current_words:
        conversations.append(
            {
                "speaker": current_speaker,
                "words": " ".join(current_words),
                "timestamps": current_timestamps,
                "confidence": current_confidence,
            }
        )

    if not conversations:
        raise ValueError("No valid conversation turns found in transcript")

    return {"conversations": conversations}
