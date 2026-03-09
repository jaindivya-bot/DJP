#!/usr/bin/env python3
"""
Phase 1.1 — YouTube Metadata Extraction

Two modes:
  1. YouTube Data API v3 (requires YOUTUBE_API_KEY)
  2. yt-dlp fallback (requires yt-dlp installed)

Outputs: raw/youtube_metadata.json
"""

import json
import subprocess
import sys
from datetime import datetime

from tqdm import tqdm

from config import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, RAW_DIR


# ──────────────────────────────────────────────────────────────────────
# API-based extraction
# ──────────────────────────────────────────────────────────────────────

def _iso8601_duration_to_hms(duration: str) -> str:
    """Convert ISO 8601 duration (PT1H2M3S) to hh:mm:ss."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return duration
    h, m, s = (int(x) if x else 0 for x in match.groups())
    return f"{h:02d}:{m:02d}:{s:02d}"


def extract_via_api(channel_id: str, api_key: str) -> list[dict]:
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=api_key)

    # Step 1: get uploads playlist ID
    ch_resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    uploads_playlist = ch_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Step 2: paginate through all videos in the uploads playlist
    video_ids: list[str] = []
    next_page = None
    while True:
        pl_resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist,
            maxResults=50,
            pageToken=next_page,
        ).execute()
        video_ids.extend(item["contentDetails"]["videoId"] for item in pl_resp["items"])
        next_page = pl_resp.get("nextPageToken")
        if not next_page:
            break

    print(f"Found {len(video_ids)} videos in uploads playlist.")

    # Step 3: fetch full metadata in batches of 50
    videos: list[dict] = []
    for i in tqdm(range(0, len(video_ids), 50), desc="Fetching video details"):
        batch = video_ids[i : i + 50]
        v_resp = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch),
        ).execute()
        for item in v_resp["items"]:
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            videos.append({
                "video_id": item["id"],
                "title": snippet["title"],
                "publish_date": snippet["publishedAt"][:10],
                "duration": _iso8601_duration_to_hms(item["contentDetails"]["duration"]),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "description": snippet.get("description", ""),
                "tags": snippet.get("tags", []),
                "thumbnail_url": snippet["thumbnails"].get("maxres", snippet["thumbnails"].get("high", {})).get("url", ""),
                "url": f"https://youtube.com/watch?v={item['id']}",
            })

    return videos


# ──────────────────────────────────────────────────────────────────────
# yt-dlp fallback
# ──────────────────────────────────────────────────────────────────────

def extract_via_ytdlp(channel_url: str) -> list[dict]:
    """Use yt-dlp to extract metadata for every video on the channel."""
    print("Using yt-dlp fallback (no API key provided)...")
    print("This may take a while for large channels.\n")

    # Use yt-dlp JSON dump for rich metadata
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    videos: list[dict] = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        data = json.loads(line)
        vid_id = data.get("id", "")
        videos.append({
            "video_id": vid_id,
            "title": data.get("title", ""),
            "publish_date": _format_ytdlp_date(data.get("upload_date", "")),
            "duration": _seconds_to_hms(data.get("duration", 0)),
            "view_count": int(data.get("view_count", 0) or 0),
            "like_count": int(data.get("like_count", 0) or 0),
            "comment_count": int(data.get("comment_count", 0) or 0),
            "description": data.get("description", ""),
            "tags": data.get("tags", []) or [],
            "thumbnail_url": data.get("thumbnail", ""),
            "url": f"https://youtube.com/watch?v={vid_id}",
        })

    print(f"Extracted metadata for {len(videos)} videos via yt-dlp.")
    return videos


def _format_ytdlp_date(date_str: str) -> str:
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def _seconds_to_hms(seconds) -> str:
    seconds = int(seconds or 0)
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    output_path = RAW_DIR / "youtube_metadata.json"

    if YOUTUBE_API_KEY and YOUTUBE_CHANNEL_ID:
        print("Using YouTube Data API v3...")
        videos = extract_via_api(YOUTUBE_CHANNEL_ID, YOUTUBE_API_KEY)
    elif YOUTUBE_CHANNEL_ID:
        # Treat channel ID as URL-able identifier
        channel_url = (
            YOUTUBE_CHANNEL_ID
            if YOUTUBE_CHANNEL_ID.startswith("http")
            else f"https://www.youtube.com/channel/{YOUTUBE_CHANNEL_ID}"
        )
        videos = extract_via_ytdlp(channel_url)
    else:
        print("ERROR: Set YOUTUBE_CHANNEL_ID in .env (and optionally YOUTUBE_API_KEY).")
        sys.exit(1)

    # Sort by publish date descending
    videos.sort(key=lambda v: v["publish_date"], reverse=True)

    with open(output_path, "w") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(videos)} videos to {output_path}")


if __name__ == "__main__":
    main()
