#!/usr/bin/env python3
"""
Phase 2.3–2.4 — AI-Powered Instagram Analysis + Master DB

For each Instagram post, call Claude for structured analysis,
then compile into instagram_master_database.csv.

Outputs:
  analysis/instagram/{post_id}.json
  databases/instagram_master_database.csv
"""

import json
import sys
import time

import anthropic
import pandas as pd
from tqdm import tqdm

from config import (
    ANALYSIS_IG_DIR,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    DATABASES_DIR,
    RAW_DIR,
)

ANALYSIS_PROMPT = """\
You are analyzing an Instagram post from "The Divya Jain Podcast" (@thedivyajainpodcast).
The account covers Business, Education, Health, and Spirituality for 20-somethings.

Post type: {post_type}
Caption: {caption}
Hashtags: {hashtags}

Extract the following in JSON format (return ONLY valid JSON, no markdown fences):

{{
  "primary_topic": "Main topic of this post",
  "content_pillar": "Business | Education | Health | Spirituality | Mixed",
  "post_category": "Podcast clip | Motivational quote | Educational carousel | Personal story | Behind-the-scenes | Promotional | Guest feature | Tips/Listicle",
  "key_message": "The single core message of this post in one sentence",
  "expandable": true,
  "expansion_angle": "If expandable, what angle would the blog take? (or null)",
  "related_youtube_episode": "Best guess of which YouTube episode this relates to, or null",
  "seo_keywords": ["3-5 keywords this content could rank for"],
  "suggested_url_slug": "if-this-became-a-page-on-the-website",
  "engagement_quality": "High | Medium | Low"
}}"""


def analyze_post(client: anthropic.Anthropic, post: dict) -> dict:
    prompt = ANALYSIS_PROMPT.format(
        post_type=post.get("post_type", ""),
        caption=post.get("caption", ""),
        hashtags=", ".join(post.get("hashtags", [])),
    )
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def compile_master_db():
    """Merge raw instagram data + analysis into CSV."""
    export_path = RAW_DIR / "instagram_export.json"
    if not export_path.exists():
        return

    with open(export_path) as f:
        posts = json.load(f)

    rows = []
    for p in posts:
        pid = p["post_id"]
        analysis_path = ANALYSIS_IG_DIR / f"{pid}.json"

        row = {
            "post_id": pid,
            "post_type": p.get("post_type", ""),
            "caption": p.get("caption", "")[:500],  # truncate for CSV
            "publish_date": p.get("publish_date", ""),
            "like_count": p.get("like_count", 0),
            "comment_count": p.get("comment_count", 0),
            "url": p.get("url", ""),
            "hashtags": "|".join(p.get("hashtags", [])),
            "is_carousel": p.get("is_carousel", False),
            "carousel_slide_count": p.get("carousel_slide_count", 0),
        }

        if analysis_path.exists():
            with open(analysis_path) as f:
                a = json.load(f)
            row.update({
                "primary_topic": a.get("primary_topic", ""),
                "content_pillar": a.get("content_pillar", ""),
                "post_category": a.get("post_category", ""),
                "key_message": a.get("key_message", ""),
                "expandable": a.get("expandable", ""),
                "expansion_angle": a.get("expansion_angle") or "",
                "related_youtube_episode": a.get("related_youtube_episode") or "",
                "seo_keywords": "|".join(a.get("seo_keywords", [])),
                "suggested_url_slug": a.get("suggested_url_slug", ""),
                "engagement_quality": a.get("engagement_quality", ""),
            })

        rows.append(row)

    df = pd.DataFrame(rows)
    output = DATABASES_DIR / "instagram_master_database.csv"
    df.to_csv(output, index=False)
    print(f"Saved {len(df)} rows to {output}")


def main():
    export_path = RAW_DIR / "instagram_export.json"
    if not export_path.exists():
        print("ERROR: Run step5_instagram_extract.py first.")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY in .env")
        sys.exit(1)

    with open(export_path) as f:
        posts = json.load(f)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    to_analyze = [
        p for p in posts
        if not (ANALYSIS_IG_DIR / f"{p['post_id']}.json").exists()
    ]

    print(f"{len(to_analyze)} posts to analyze ({len(posts) - len(to_analyze)} already done).\n")

    success, failed = 0, 0
    for post in tqdm(to_analyze, desc="Analyzing Instagram"):
        pid = post["post_id"]
        analysis_path = ANALYSIS_IG_DIR / f"{pid}.json"

        try:
            analysis = analyze_post(client, post)
            with open(analysis_path, "w") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            success += 1
        except json.JSONDecodeError as e:
            print(f"\nJSON parse error for {pid}: {e}")
            failed += 1
        except anthropic.APIError as e:
            print(f"\nAPI error for {pid}: {e}")
            failed += 1
            time.sleep(5)
        except Exception as e:
            print(f"\nError for {pid}: {e}")
            failed += 1

        time.sleep(0.5)

    print(f"\nAnalysis done: {success} succeeded, {failed} failed.")
    print("Compiling master database...")
    compile_master_db()


if __name__ == "__main__":
    main()
