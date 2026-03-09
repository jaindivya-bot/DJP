#!/usr/bin/env python3
"""
Phase 1.2 — Transcript Extraction & Cleaning

For every video in youtube_metadata.json, download transcripts using
youtube-transcript-api (primary) or yt-dlp subtitles (fallback).

Outputs:
  raw/transcripts/{video_id}.txt   — cleaned plain text
  raw/transcripts/{video_id}.json  — timestamped segments
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from tqdm import tqdm

from config import RAW_DIR, TRANSCRIPTS_DIR


# ──────────────────────────────────────────────────────────────────────
# Cleaning
# ──────────────────────────────────────────────────────────────────────

NOISE_PATTERNS = re.compile(
    r"\[(?:Music|Applause|Laughter|Cheering|Silence|Inaudible|Foreign)\]",
    re.IGNORECASE,
)


def clean_text(segments: list[dict]) -> str:
    """Merge timestamped segments into clean paragraphs."""
    lines: list[str] = []
    for seg in segments:
        text = seg.get("text", "").strip()
        text = NOISE_PATTERNS.sub("", text).strip()
        if text:
            lines.append(text)

    # Merge into paragraphs: break every ~5 sentences or on long pauses
    paragraphs: list[str] = []
    current: list[str] = []
    for i, line in enumerate(lines):
        current.append(line)
        # Heuristic: paragraph break every 5-7 lines
        if len(current) >= 6 or (line.endswith((".", "!", "?")) and len(current) >= 3):
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


# ──────────────────────────────────────────────────────────────────────
# Primary: youtube-transcript-api
# ──────────────────────────────────────────────────────────────────────

def fetch_transcript_api(video_id: str) -> list[dict] | None:
    """Return list of {text, start, duration} or None on failure."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        return segments
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────
# Fallback: yt-dlp subtitles
# ──────────────────────────────────────────────────────────────────────

def fetch_transcript_ytdlp(video_id: str) -> list[dict] | None:
    """Download auto-subs via yt-dlp and parse into segments."""
    url = f"https://youtube.com/watch?v={video_id}"
    tmp_dir = TRANSCRIPTS_DIR / "_tmp"
    tmp_dir.mkdir(exist_ok=True)
    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "json3",
        "--skip-download",
        "-o", str(tmp_dir / "%(id)s"),
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    # Find the subtitle file
    sub_file = None
    for ext in [".en.json3", ".en.json"]:
        candidate = tmp_dir / f"{video_id}{ext}"
        if candidate.exists():
            sub_file = candidate
            break

    if not sub_file:
        return None

    with open(sub_file) as f:
        data = json.load(f)

    segments = []
    for event in data.get("events", []):
        text_parts = [seg.get("utf8", "") for seg in event.get("segs", [])]
        text = "".join(text_parts).strip()
        if text:
            segments.append({
                "text": text,
                "start": event.get("tStartMs", 0) / 1000,
                "duration": event.get("dDurationMs", 0) / 1000,
            })

    # Clean up temp files
    sub_file.unlink(missing_ok=True)
    return segments if segments else None


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    metadata_path = RAW_DIR / "youtube_metadata.json"
    if not metadata_path.exists():
        print("ERROR: Run step1_youtube_metadata.py first.")
        sys.exit(1)

    with open(metadata_path) as f:
        videos = json.load(f)

    print(f"Extracting transcripts for {len(videos)} videos...\n")

    success, failed = 0, 0
    failed_ids: list[str] = []

    for video in tqdm(videos, desc="Transcripts"):
        vid = video["video_id"]
        txt_path = TRANSCRIPTS_DIR / f"{vid}.txt"
        json_path = TRANSCRIPTS_DIR / f"{vid}.json"

        # Skip if already extracted
        if txt_path.exists() and json_path.exists():
            success += 1
            continue

        # Try primary, then fallback
        segments = fetch_transcript_api(vid)
        if segments is None:
            segments = fetch_transcript_ytdlp(vid)

        if segments is None:
            failed += 1
            failed_ids.append(vid)
            continue

        # Save timestamped JSON
        with open(json_path, "w") as f:
            json.dump(segments, f, indent=2, ensure_ascii=False)

        # Save cleaned plain text
        cleaned = clean_text(segments)
        with open(txt_path, "w") as f:
            f.write(cleaned)

        success += 1

    print(f"\nDone: {success} succeeded, {failed} failed.")
    if failed_ids:
        fail_log = RAW_DIR / "transcript_failures.json"
        with open(fail_log, "w") as f:
            json.dump(failed_ids, f, indent=2)
        print(f"Failed video IDs saved to {fail_log}")


if __name__ == "__main__":
    main()
