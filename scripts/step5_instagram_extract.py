#!/usr/bin/env python3
"""
Phase 2.1–2.2 — Instagram Content Extraction

Three modes:
  1. Instagram data export JSON (from Settings → Download Your Information)
  2. instaloader (Python package)
  3. Manual CSV upload

Outputs: raw/instagram_export.json
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from config import INSTAGRAM_EXPORT_PATH, INSTAGRAM_HANDLE, RAW_DIR


# ──────────────────────────────────────────────────────────────────────
# Method 1: Instagram official data export
# ──────────────────────────────────────────────────────────────────────

def parse_instagram_export(export_path: str) -> list[dict]:
    """Parse Instagram's official JSON data export."""
    export_dir = Path(export_path)

    # Instagram export structure varies; look for posts
    posts_data = []
    candidates = [
        export_dir / "content" / "posts_1.json",
        export_dir / "media.json",
        export_dir / "posts" / "media.json",
    ]

    raw_posts = []
    for candidate in candidates:
        if candidate.exists():
            with open(candidate) as f:
                data = json.load(f)
            if isinstance(data, list):
                raw_posts = data
            elif isinstance(data, dict):
                raw_posts = data.get("ig_media", data.get("posts", []))
            break

    if not raw_posts:
        # Try to find any JSON with post-like data
        for json_file in export_dir.rglob("*.json"):
            with open(json_file) as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue
            if isinstance(data, list) and len(data) > 5:
                sample = data[0] if data else {}
                if any(k in str(sample) for k in ["caption", "media", "title"]):
                    raw_posts = data
                    break

    for post in raw_posts:
        caption = ""
        if isinstance(post.get("caption"), str):
            caption = post["caption"]
        elif isinstance(post.get("caption"), dict):
            caption = post["caption"].get("text", "")
        elif "title" in post:
            caption = post.get("title", "")
            if not caption and "media" in post:
                media = post["media"]
                if isinstance(media, list) and media:
                    caption = media[0].get("title", "")

        hashtags = re.findall(r"#(\w+)", caption)

        posts_data.append({
            "post_id": post.get("id", post.get("pk", "")),
            "post_type": _infer_post_type(post),
            "caption": caption,
            "publish_date": post.get("taken_at", post.get("creation_timestamp", "")),
            "like_count": post.get("like_count", 0),
            "comment_count": post.get("comment_count", 0),
            "url": post.get("permalink", ""),
            "hashtags": hashtags,
            "media_urls": _extract_media_urls(post),
            "is_carousel": post.get("media_type") == "CAROUSEL_ALBUM" or post.get("carousel_media_count", 0) > 0,
            "carousel_slide_count": post.get("carousel_media_count", 0),
        })

    return posts_data


def _infer_post_type(post: dict) -> str:
    media_type = post.get("media_type", "").upper()
    if media_type == "VIDEO" or post.get("video_duration"):
        return "Reel"
    if media_type == "CAROUSEL_ALBUM" or post.get("carousel_media_count", 0) > 1:
        return "Carousel"
    return "Single Image"


def _extract_media_urls(post: dict) -> list[str]:
    urls = []
    if "media_url" in post:
        urls.append(post["media_url"])
    for item in post.get("carousel_media", post.get("children", {}).get("data", [])):
        if "media_url" in item:
            urls.append(item["media_url"])
    return urls


# ──────────────────────────────────────────────────────────────────────
# Method 2: instaloader
# ──────────────────────────────────────────────────────────────────────

def extract_via_instaloader(handle: str) -> list[dict]:
    """Use instaloader to download post metadata."""
    print(f"Using instaloader to extract posts from @{handle}...")
    print("Note: This may require login for private accounts or rate-limited requests.\n")

    import instaloader

    L = instaloader.Instaloader(
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=True,
        compress_json=False,
    )

    try:
        profile = instaloader.Profile.from_username(L.context, handle)
    except Exception as e:
        print(f"Error loading profile: {e}")
        print("You may need to log in: instaloader --login YOUR_USERNAME")
        sys.exit(1)

    posts_data = []
    for post in profile.get_posts():
        hashtags = list(post.caption_hashtags) if post.caption_hashtags else []
        caption = post.caption or ""

        post_type = "Single Image"
        if post.is_video:
            post_type = "Reel"
        elif post.typename == "GraphSidecar":
            post_type = "Carousel"

        posts_data.append({
            "post_id": post.shortcode,
            "post_type": post_type,
            "caption": caption,
            "publish_date": post.date_utc.isoformat()[:10],
            "like_count": post.likes,
            "comment_count": post.comments,
            "url": f"https://www.instagram.com/p/{post.shortcode}/",
            "hashtags": hashtags,
            "media_urls": [post.url],
            "is_carousel": post.typename == "GraphSidecar",
            "carousel_slide_count": post.mediacount if hasattr(post, "mediacount") else 0,
        })

    print(f"Extracted {len(posts_data)} posts via instaloader.")
    return posts_data


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    output_path = RAW_DIR / "instagram_export.json"

    if INSTAGRAM_EXPORT_PATH and Path(INSTAGRAM_EXPORT_PATH).exists():
        print("Parsing Instagram data export...")
        posts = parse_instagram_export(INSTAGRAM_EXPORT_PATH)
    elif INSTAGRAM_HANDLE:
        posts = extract_via_instaloader(INSTAGRAM_HANDLE)
    else:
        print("ERROR: Set INSTAGRAM_HANDLE or INSTAGRAM_EXPORT_PATH in .env")
        sys.exit(1)

    # Sort by date descending
    posts.sort(key=lambda p: p.get("publish_date", ""), reverse=True)

    with open(output_path, "w") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(posts)} posts to {output_path}")


if __name__ == "__main__":
    main()
