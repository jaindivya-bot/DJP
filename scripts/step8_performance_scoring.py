#!/usr/bin/env python3
"""
Phase 4 — Content Quality & Performance Scoring

4.1 Compute performance_score for each content piece
4.2 Classify evergreen vs timely

Outputs: databases/content_performance_rankings.csv
"""

import json
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config import DATABASES_DIR


def compute_performance_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate normalized performance score per content piece."""
    if df.empty:
        return df

    now = datetime.now()
    six_months_ago = now - timedelta(days=180)
    one_year_ago = now - timedelta(days=365)

    # Normalize views
    max_views = max(df["view_count"].max(), 1)
    df["normalized_views"] = df["view_count"] / max_views

    # Engagement rate
    df["engagement_rate"] = (df["like_count"] + df["comment_count"]) / df["view_count"].replace(0, 1)
    max_engagement = max(df["engagement_rate"].max(), 0.001)
    df["normalized_engagement"] = df["engagement_rate"] / max_engagement

    # Quality score (normalize to 0-1)
    df["quality_normalized"] = pd.to_numeric(df["episode_quality_score"], errors="coerce").fillna(5) / 10

    # Recency bonus
    def recency(date_str):
        try:
            pub = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            if pub >= six_months_ago:
                return 1.0
            elif pub >= one_year_ago:
                return 0.7
            else:
                return 0.4
        except (ValueError, TypeError):
            return 0.4

    df["recency_bonus"] = df["publish_date"].apply(recency)

    # Final score
    df["performance_score"] = (
        0.4 * df["normalized_views"]
        + 0.3 * df["normalized_engagement"]
        + 0.2 * df["quality_normalized"]
        + 0.1 * df["recency_bonus"]
    ).round(4)

    return df


def classify_evergreen(df: pd.DataFrame) -> pd.DataFrame:
    """Heuristic classification of evergreen vs timely content."""
    timely_signals = [
        r"\b20\d{2}\b",  # year mentions
        r"\breact(?:ing|ion)\b",
        r"\btrending\b",
        r"\bnews\b",
        r"\blatest\b",
        r"\bupdate\b",
        r"\brecent\b",
    ]

    evergreen_signals = [
        r"\bhow to\b",
        r"\bguide\b",
        r"\btips\b",
        r"\badvice\b",
        r"\blessons?\b",
        r"\bprinciples?\b",
        r"\bstrateg(?:y|ies)\b",
        r"\bmindset\b",
        r"\bhabits?\b",
    ]

    def classify(title):
        title_lower = str(title).lower()
        timely_count = sum(1 for p in timely_signals if __import__("re").search(p, title_lower))
        evergreen_count = sum(1 for p in evergreen_signals if __import__("re").search(p, title_lower))

        if timely_count > evergreen_count:
            return "Timely"
        elif evergreen_count > 0:
            return "Evergreen"
        else:
            return "Semi-evergreen"

    df["content_freshness"] = df["title_or_caption"].apply(classify)
    return df


def main():
    unified_path = DATABASES_DIR / "unified_content_index.csv"
    if not unified_path.exists():
        print("ERROR: Run step7 (cross-platform audit) first.")
        sys.exit(1)

    df = pd.read_csv(unified_path)
    print(f"Loaded {len(df)} content pieces.")

    df = compute_performance_scores(df)
    df = classify_evergreen(df)

    # Sort by performance score
    df = df.sort_values("performance_score", ascending=False)

    # Select output columns
    output_cols = [
        "content_id", "platform", "title_or_caption", "publish_date",
        "content_type", "primary_topic", "content_pillar",
        "view_count", "like_count", "comment_count",
        "performance_score", "content_freshness",
        "url", "suggested_url_slug",
    ]
    existing_cols = [c for c in output_cols if c in df.columns]
    out = df[existing_cols]

    output = DATABASES_DIR / "content_performance_rankings.csv"
    out.to_csv(output, index=False)
    print(f"Performance rankings: {len(out)} rows saved to {output}")


if __name__ == "__main__":
    main()
