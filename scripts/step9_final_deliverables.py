#!/usr/bin/env python3
"""
Phase 5 — Final Deliverables

Generate:
  databases/pseo_page_plan.csv
  reports/editorial_calendar_suggestions.csv
"""

import json
import sys

import pandas as pd

from config import DATABASES_DIR, REPORTS_DIR


def generate_pseo_plan() -> pd.DataFrame:
    """Create the pSEO page plan from all collected data."""
    pages = []

    # ── Episode pages (from YouTube) ──
    yt_path = DATABASES_DIR / "youtube_master_database.csv"
    if yt_path.exists():
        yt = pd.read_csv(yt_path)
        for _, r in yt.iterrows():
            slug = str(r.get("suggested_url_slug", "")).strip()
            if not slug or slug == "nan":
                slug = str(r["video_id"])

            pages.append({
                "page_type": "Episode",
                "url_slug": f"/episodes/{slug}",
                "title": r["title"],
                "source_content_ids": r["video_id"],
                "platform": "youtube",
                "target_keywords": r.get("seo_keywords", ""),
                "content_pillar": r.get("content_pillar", ""),
                "has_transcript": True,
                "has_blog_rewrite": bool(r.get("summary_long")),
                "priority": _episode_priority(r),
            })

    # ── Topic hub pages (from clusters) ──
    clusters_path = DATABASES_DIR / "topic_clusters.json"
    if clusters_path.exists():
        with open(clusters_path) as f:
            clusters = json.load(f)

        for key, c in clusters.items():
            if not c.get("has_enough_depth", False):
                continue
            all_ids = c.get("youtube_ids", []) + c.get("instagram_ids", [])
            pages.append({
                "page_type": "Topic Hub",
                "url_slug": c.get("suggested_hub_url", f"/topics/{key}"),
                "title": f"{c['label']} — Everything You Need to Know",
                "source_content_ids": "|".join(all_ids),
                "platform": "cross-platform",
                "target_keywords": "|".join(c.get("top_keywords", [])[:5]),
                "content_pillar": c.get("pillar", "Mixed"),
                "has_transcript": False,
                "has_blog_rewrite": False,
                "priority": min(10, c.get("content_count", 0) + 3),
            })

    # ── Guest pages ──
    guest_path = DATABASES_DIR / "guest_directory.csv"
    if guest_path.exists():
        guests = pd.read_csv(guest_path)
        for _, g in guests.iterrows():
            name = str(g.get("guest_name", "")).strip()
            if not name or name == "nan":
                continue
            pages.append({
                "page_type": "Guest Profile",
                "url_slug": str(g.get("suggested_guest_page_url", "")),
                "title": f"{name} on The Divya Jain Podcast",
                "source_content_ids": str(g.get("episodes_appeared_in", "")),
                "platform": "youtube",
                "target_keywords": f"{name}|{g.get('expertise_area', '')}",
                "content_pillar": "",
                "has_transcript": False,
                "has_blog_rewrite": False,
                "priority": 6,
            })

    # ── Expandable Instagram posts as standalone pages ──
    ig_path = DATABASES_DIR / "instagram_master_database.csv"
    if ig_path.exists():
        ig = pd.read_csv(ig_path)
        expandable = ig[ig.get("expandable", pd.Series(dtype=bool)) == True] if "expandable" in ig.columns else pd.DataFrame()
        for _, r in expandable.iterrows():
            slug = str(r.get("suggested_url_slug", "")).strip()
            if not slug or slug == "nan":
                continue
            pages.append({
                "page_type": "Instagram Expansion",
                "url_slug": f"/insights/{slug}",
                "title": str(r.get("key_message", str(r.get("caption", ""))[:80])),
                "source_content_ids": str(r["post_id"]),
                "platform": "instagram",
                "target_keywords": str(r.get("seo_keywords", "")),
                "content_pillar": str(r.get("content_pillar", "")),
                "has_transcript": False,
                "has_blog_rewrite": False,
                "priority": 4,
            })

    df = pd.DataFrame(pages)
    df = df.sort_values("priority", ascending=False)

    output = DATABASES_DIR / "pseo_page_plan.csv"
    df.to_csv(output, index=False)
    print(f"pSEO page plan: {len(df)} pages saved to {output}")
    return df


def _episode_priority(row) -> int:
    score = 5
    views = int(row.get("view_count", 0) or 0)
    if views > 100000:
        score += 3
    elif views > 50000:
        score += 2
    elif views > 10000:
        score += 1

    quality = row.get("episode_quality_score", 5)
    try:
        quality = float(quality)
    except (ValueError, TypeError):
        quality = 5
    if quality >= 8:
        score += 1

    return min(10, score)


def generate_editorial_calendar() -> pd.DataFrame:
    """Identify content gaps and suggest new episodes/posts."""
    gap_path = DATABASES_DIR / "gap_analysis.csv"
    clusters_path = DATABASES_DIR / "topic_clusters.json"

    suggestions = []

    if gap_path.exists():
        gaps = pd.read_csv(gap_path)
        # Focus on "gap" type (high search volume, little content)
        content_gaps = gaps[gaps["gap_type"] == "gap"]
        for _, r in content_gaps.iterrows():
            suggestions.append({
                "suggestion_type": "New Episode",
                "topic": r["topic_cluster"],
                "rationale": "High keyword demand but insufficient existing content",
                "target_keywords": r.get("primary_keywords", ""),
                "estimated_search_volume": r.get("estimated_monthly_searches", "N/A"),
                "priority": r.get("priority_score", 5),
                "suggested_format": "Interview or deep-dive solo episode",
                "suggested_title": f"The Truth About {str(r['topic_cluster']).replace('-', ' ').title()}",
            })

        # Also suggest expanding niche strengths
        niches = gaps[gaps["gap_type"] == "niche"]
        for _, r in niches.iterrows():
            if int(r.get("content_count", 0)) >= 5:
                suggestions.append({
                    "suggestion_type": "Content Repurpose",
                    "topic": r["topic_cluster"],
                    "rationale": "Lots of content but low search volume — repurpose into shareable formats",
                    "target_keywords": r.get("primary_keywords", ""),
                    "estimated_search_volume": r.get("estimated_monthly_searches", "N/A"),
                    "priority": 4,
                    "suggested_format": "Instagram carousel series or YouTube Shorts compilation",
                    "suggested_title": f"Quick Guide: {str(r['topic_cluster']).replace('-', ' ').title()}",
                })

    if clusters_path.exists():
        with open(clusters_path) as f:
            clusters = json.load(f)

        # Find thin clusters that could use more content
        for key, c in clusters.items():
            if 1 <= c.get("content_count", 0) <= 2 and c.get("combined_views", 0) > 5000:
                suggestions.append({
                    "suggestion_type": "Deepen Topic",
                    "topic": key,
                    "rationale": f"Only {c['content_count']} piece(s) but good engagement — create more",
                    "target_keywords": "|".join(c.get("top_keywords", [])[:3]),
                    "estimated_search_volume": "N/A",
                    "priority": 6,
                    "suggested_format": "Follow-up episode or guest interview",
                    "suggested_title": f"More on {c['label']}: What We Didn't Cover",
                })

    df = pd.DataFrame(suggestions)
    if not df.empty:
        df = df.sort_values("priority", ascending=False)

    output = REPORTS_DIR / "editorial_calendar_suggestions.csv"
    df.to_csv(output, index=False)
    print(f"Editorial calendar: {len(df)} suggestions saved to {output}")
    return df


def main():
    print("=" * 60)
    print("Phase 5: Final Deliverables")
    print("=" * 60)

    print("\n--- Generating pSEO page plan ---")
    generate_pseo_plan()

    print("\n--- Generating editorial calendar suggestions ---")
    generate_editorial_calendar()

    print("\nAll deliverables generated.")


if __name__ == "__main__":
    main()
