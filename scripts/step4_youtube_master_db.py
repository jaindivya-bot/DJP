#!/usr/bin/env python3
"""
Phase 1.4 — Compile YouTube Master Database

Merges youtube_metadata.json + analysis/{video_id}.json into a single CSV.

Outputs: databases/youtube_master_database.csv
"""

import json
import sys

import pandas as pd

from config import ANALYSIS_YT_DIR, DATABASES_DIR, RAW_DIR


def main():
    metadata_path = RAW_DIR / "youtube_metadata.json"
    if not metadata_path.exists():
        print("ERROR: Run step1 first.")
        sys.exit(1)

    with open(metadata_path) as f:
        videos = json.load(f)

    rows = []
    for v in videos:
        vid = v["video_id"]
        analysis_path = ANALYSIS_YT_DIR / f"{vid}.json"

        row = {
            "video_id": vid,
            "title": v["title"],
            "publish_date": v["publish_date"],
            "duration": v["duration"],
            "view_count": v["view_count"],
            "like_count": v["like_count"],
            "comment_count": v["comment_count"],
            "url": v["url"],
            "thumbnail_url": v["thumbnail_url"],
        }

        if analysis_path.exists():
            with open(analysis_path) as f:
                a = json.load(f)
            row.update({
                "primary_topic": a.get("primary_topic", ""),
                "secondary_topics": "|".join(a.get("secondary_topics", [])),
                "content_pillar": a.get("content_pillar", ""),
                "guest_name": a.get("guest_name") or "",
                "guest_title": a.get("guest_title") or "",
                "guest_expertise": a.get("guest_expertise") or "",
                "target_audience_segment": a.get("target_audience_segment", ""),
                "key_takeaways": "|".join(a.get("key_takeaways", [])),
                "summary_short": a.get("summary_short", ""),
                "summary_long": a.get("summary_long", ""),
                "seo_keywords": "|".join(a.get("seo_keywords", [])),
                "suggested_url_slug": a.get("suggested_url_slug", ""),
                "related_search_queries": "|".join(a.get("related_search_queries", [])),
                "content_format": a.get("content_format", ""),
                "emotional_tone": a.get("emotional_tone", ""),
                "episode_quality_score": a.get("episode_quality_score", ""),
            })
        else:
            # Fill with blanks for videos without analysis
            for col in [
                "primary_topic", "secondary_topics", "content_pillar",
                "guest_name", "guest_title", "guest_expertise",
                "target_audience_segment", "key_takeaways",
                "summary_short", "summary_long", "seo_keywords",
                "suggested_url_slug", "related_search_queries",
                "content_format", "emotional_tone", "episode_quality_score",
            ]:
                row[col] = ""

        rows.append(row)

    df = pd.DataFrame(rows)
    output = DATABASES_DIR / "youtube_master_database.csv"
    df.to_csv(output, index=False)
    print(f"Saved {len(df)} rows to {output}")


if __name__ == "__main__":
    main()
