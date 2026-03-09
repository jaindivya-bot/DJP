#!/usr/bin/env python3
"""
Phase 3 — Cross-Platform Content Audit

3.1 Merge databases into unified_content_index.csv
3.2 Topic clustering → topic_clusters.json
3.3 Gap analysis → gap_analysis.csv
3.4 Guest directory → guest_directory.csv

Outputs:
  databases/unified_content_index.csv
  databases/topic_clusters.json
  databases/gap_analysis.csv
  databases/guest_directory.csv
"""

import json
import re
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from config import DATABASES_DIR, KEYWORD_VOLUME_CSV_PATH


# ──────────────────────────────────────────────────────────────────────
# 3.1 Merge Databases
# ──────────────────────────────────────────────────────────────────────

def merge_databases() -> pd.DataFrame:
    yt_path = DATABASES_DIR / "youtube_master_database.csv"
    ig_path = DATABASES_DIR / "instagram_master_database.csv"

    rows = []

    if yt_path.exists():
        yt = pd.read_csv(yt_path)
        for _, r in yt.iterrows():
            rows.append({
                "content_id": r["video_id"],
                "platform": "youtube",
                "title_or_caption": r["title"],
                "publish_date": r["publish_date"],
                "content_type": r.get("content_format", "Video"),
                "primary_topic": r.get("primary_topic", ""),
                "content_pillar": r.get("content_pillar", ""),
                "guest_name": r.get("guest_name", ""),
                "seo_keywords": r.get("seo_keywords", ""),
                "url": r["url"],
                "view_count": r.get("view_count", 0),
                "like_count": r.get("like_count", 0),
                "comment_count": r.get("comment_count", 0),
                "suggested_url_slug": r.get("suggested_url_slug", ""),
                "expandable": True,  # all YT episodes are expandable
                "episode_quality_score": r.get("episode_quality_score", ""),
            })

    if ig_path.exists():
        ig = pd.read_csv(ig_path)
        for _, r in ig.iterrows():
            rows.append({
                "content_id": r["post_id"],
                "platform": "instagram",
                "title_or_caption": str(r.get("caption", ""))[:200],
                "publish_date": r.get("publish_date", ""),
                "content_type": r.get("post_type", ""),
                "primary_topic": r.get("primary_topic", ""),
                "content_pillar": r.get("content_pillar", ""),
                "guest_name": "",
                "seo_keywords": r.get("seo_keywords", ""),
                "url": r.get("url", ""),
                "view_count": 0,
                "like_count": r.get("like_count", 0),
                "comment_count": r.get("comment_count", 0),
                "suggested_url_slug": r.get("suggested_url_slug", ""),
                "expandable": r.get("expandable", False),
                "episode_quality_score": "",
            })

    df = pd.DataFrame(rows)

    # Compute normalized engagement score
    if not df.empty:
        max_views = max(df["view_count"].max(), 1)
        max_likes = max(df["like_count"].max(), 1)
        df["engagement_score"] = (
            0.5 * df["like_count"] / max_likes
            + 0.3 * df["comment_count"] / max(df["comment_count"].max(), 1)
            + 0.2 * df["view_count"] / max_views
        ).round(4)
    else:
        df["engagement_score"] = []

    df["related_content_ids"] = ""  # populated during clustering

    output = DATABASES_DIR / "unified_content_index.csv"
    df.to_csv(output, index=False)
    print(f"Unified index: {len(df)} rows saved to {output}")
    return df


# ──────────────────────────────────────────────────────────────────────
# 3.2 Topic Clustering
# ──────────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def _normalize_topic(topic: str) -> str:
    """Basic topic normalization."""
    topic = topic.lower().strip()
    # Common synonyms
    replacements = {
        "career change": "career-transitions",
        "switching careers": "career-transitions",
        "career transition": "career-transitions",
        "career switch": "career-transitions",
        "mental health": "mental-health",
        "anxiety": "mental-health",
        "depression": "mental-health",
        "personal branding": "personal-brand",
        "building a personal brand": "personal-brand",
        "personal brand": "personal-brand",
        "self growth": "self-growth",
        "self-improvement": "self-growth",
        "personal growth": "self-growth",
        "personal development": "self-growth",
        "startup": "entrepreneurship",
        "startups": "entrepreneurship",
        "starting a business": "entrepreneurship",
        "building a business": "entrepreneurship",
    }
    for pattern, replacement in replacements.items():
        if pattern in topic:
            return replacement
    return _slugify(topic)


def cluster_topics(df: pd.DataFrame) -> dict:
    """Group content by normalized topic clusters."""
    clusters: dict[str, dict] = {}

    for _, row in df.iterrows():
        topic = str(row.get("primary_topic", "")).strip()
        if not topic:
            continue

        cluster_key = _normalize_topic(topic)
        if not cluster_key:
            continue

        if cluster_key not in clusters:
            # Infer pillar from the first item
            pillar = str(row.get("content_pillar", "Mixed"))
            clusters[cluster_key] = {
                "label": topic.title(),
                "pillar": pillar,
                "content_count": 0,
                "youtube_ids": [],
                "instagram_ids": [],
                "combined_views": 0,
                "top_keywords": [],
                "suggested_hub_url": f"/topics/{cluster_key}",
                "has_enough_depth": False,
            }

        c = clusters[cluster_key]
        c["content_count"] += 1
        c["combined_views"] += int(row.get("view_count", 0) or 0)

        if row["platform"] == "youtube":
            c["youtube_ids"].append(row["content_id"])
        else:
            c["instagram_ids"].append(row["content_id"])

        # Collect keywords
        kw = str(row.get("seo_keywords", ""))
        if kw:
            c["top_keywords"].extend(kw.split("|"))

    # Deduplicate keywords and set depth flag
    for key, c in clusters.items():
        c["top_keywords"] = list(set(c["top_keywords"]))[:15]
        c["has_enough_depth"] = c["content_count"] >= 3

    # Sort by content count descending
    clusters = dict(sorted(clusters.items(), key=lambda x: x[1]["content_count"], reverse=True))

    output = DATABASES_DIR / "topic_clusters.json"
    with open(output, "w") as f:
        json.dump(clusters, f, indent=2, ensure_ascii=False)

    print(f"Topic clusters: {len(clusters)} clusters saved to {output}")
    return clusters


# ──────────────────────────────────────────────────────────────────────
# 3.3 Gap Analysis
# ──────────────────────────────────────────────────────────────────────

def gap_analysis(clusters: dict) -> pd.DataFrame:
    """Compare topic clusters against keyword demand if available."""
    keyword_volumes: dict[str, int] = {}

    if KEYWORD_VOLUME_CSV_PATH:
        try:
            kw_df = pd.read_csv(KEYWORD_VOLUME_CSV_PATH)
            # Try common column names for keyword/volume
            kw_col = next((c for c in kw_df.columns if "keyword" in c.lower()), kw_df.columns[0])
            vol_col = next((c for c in kw_df.columns if "volume" in c.lower() or "search" in c.lower()), kw_df.columns[1])
            for _, r in kw_df.iterrows():
                keyword_volumes[str(r[kw_col]).lower()] = int(r[vol_col])
        except Exception as e:
            print(f"Warning: could not load keyword volume CSV: {e}")

    rows = []
    for cluster_key, c in clusters.items():
        # Estimate search volume from keywords
        est_volume = 0
        primary_keywords = c.get("top_keywords", [])[:5]
        for kw in primary_keywords:
            est_volume += keyword_volumes.get(kw.lower(), 0)

        content_count = c["content_count"]
        total_views = c["combined_views"]
        avg_engagement = total_views / max(content_count, 1)

        # Classify gap type
        has_content = content_count >= 3
        has_volume = est_volume > 100  # threshold

        if has_volume and has_content:
            gap_type = "strength"
            priority = 9
        elif has_volume and not has_content:
            gap_type = "gap"
            priority = 8
        elif not has_volume and has_content:
            gap_type = "niche"
            priority = 5
        else:
            gap_type = "skip"
            priority = 2

        # Adjust priority by views
        if total_views > 50000:
            priority = min(10, priority + 1)

        recommended_action = {
            "strength": "Create priority hub page — launch first",
            "gap": "Create new episodes targeting these keywords",
            "niche": "Build niche authority page — lower priority",
            "skip": "Skip for now — revisit later",
        }[gap_type]

        rows.append({
            "topic_cluster": cluster_key,
            "content_count": content_count,
            "total_views": total_views,
            "avg_engagement": round(avg_engagement, 1),
            "primary_keywords": "|".join(primary_keywords),
            "estimated_monthly_searches": est_volume if est_volume else "N/A (no keyword data)",
            "gap_type": gap_type,
            "priority_score": priority,
            "recommended_action": recommended_action,
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("priority_score", ascending=False)

    output = DATABASES_DIR / "gap_analysis.csv"
    df.to_csv(output, index=False)
    print(f"Gap analysis: {len(df)} rows saved to {output}")
    return df


# ──────────────────────────────────────────────────────────────────────
# 3.4 Guest Directory
# ──────────────────────────────────────────────────────────────────────

def build_guest_directory() -> pd.DataFrame:
    yt_path = DATABASES_DIR / "youtube_master_database.csv"
    if not yt_path.exists():
        print("No YouTube database found — skipping guest directory.")
        return pd.DataFrame()

    yt = pd.read_csv(yt_path)

    guests: dict[str, dict] = {}
    for _, r in yt.iterrows():
        name = str(r.get("guest_name", "")).strip()
        if not name or name.lower() in ("", "nan", "null", "none"):
            continue

        if name not in guests:
            guests[name] = {
                "guest_name": name,
                "guest_title": str(r.get("guest_title", "")) if str(r.get("guest_title", "")) != "nan" else "",
                "expertise_area": str(r.get("guest_expertise", "")) if str(r.get("guest_expertise", "")) != "nan" else "",
                "episodes_appeared_in": [],
                "total_views_across_episodes": 0,
                "topics_discussed": [],
            }

        g = guests[name]
        g["episodes_appeared_in"].append(r["video_id"])
        g["total_views_across_episodes"] += int(r.get("view_count", 0) or 0)
        topic = str(r.get("primary_topic", ""))
        if topic and topic != "nan":
            g["topics_discussed"].append(topic)

    rows = []
    for g in guests.values():
        slug = _slugify(g["guest_name"])
        rows.append({
            "guest_name": g["guest_name"],
            "guest_title": g["guest_title"],
            "expertise_area": g["expertise_area"],
            "episodes_appeared_in": "|".join(g["episodes_appeared_in"]),
            "total_views_across_episodes": g["total_views_across_episodes"],
            "topics_discussed": "|".join(set(g["topics_discussed"])),
            "suggested_guest_page_url": f"/guests/{slug}",
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("total_views_across_episodes", ascending=False)

    output = DATABASES_DIR / "guest_directory.csv"
    df.to_csv(output, index=False)
    print(f"Guest directory: {len(df)} guests saved to {output}")
    return df


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Phase 3: Cross-Platform Content Audit")
    print("=" * 60)

    print("\n--- 3.1 Merging databases ---")
    df = merge_databases()

    print("\n--- 3.2 Topic clustering ---")
    clusters = cluster_topics(df)

    print("\n--- 3.3 Gap analysis ---")
    gap_analysis(clusters)

    print("\n--- 3.4 Guest directory ---")
    build_guest_directory()

    print("\nPhase 3 complete.")


if __name__ == "__main__":
    main()
