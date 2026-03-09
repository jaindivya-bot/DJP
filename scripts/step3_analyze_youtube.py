#!/usr/bin/env python3
"""
Phase 1.3 — AI-Powered Content Analysis (YouTube)

For each video transcript, call Claude to extract structured data.
Processes in batches and handles long transcripts by chunking.

Outputs: analysis/youtube/{video_id}.json
"""

import json
import sys
import time

import anthropic
from tqdm import tqdm

from config import (
    ANTHROPIC_API_KEY,
    ANALYSIS_BATCH_SIZE,
    ANALYSIS_YT_DIR,
    CLAUDE_MODEL,
    MAX_TRANSCRIPT_CHARS,
    RAW_DIR,
    TRANSCRIPTS_DIR,
)

ANALYSIS_PROMPT = """\
You are analyzing a podcast transcript from "The Divya Jain Podcast".
The podcast covers Business, Education, Health, and Spirituality for a 20-something audience.

Here is the transcript:
<transcript>
{transcript}
</transcript>

Video title: {title}
Video description: {description}

Extract the following in JSON format (return ONLY valid JSON, no markdown fences):

{{
  "primary_topic": "The single main topic of this episode",
  "secondary_topics": ["2-4 secondary topics discussed"],
  "content_pillar": "One of: Business | Education | Health | Spirituality | Mixed",
  "guest_name": "Full name of guest, or null if solo episode",
  "guest_title": "Guest's role/designation, or null",
  "guest_expertise": "What the guest is known for, or null",
  "target_audience_segment": "Who specifically would benefit most from this episode",
  "key_takeaways": [
    "Takeaway 1 — one clear, actionable sentence",
    "Takeaway 2",
    "Takeaway 3",
    "Takeaway 4",
    "Takeaway 5"
  ],
  "quotable_moments": [
    {{
      "quote": "Exact compelling quote from the episode",
      "speaker": "Who said it",
      "timestamp_approx": "Approximate timestamp if available"
    }}
  ],
  "summary_short": "1-2 sentence summary for meta descriptions (under 160 characters)",
  "summary_long": "3-5 sentence summary for a blog intro paragraph",
  "blog_rewrite": "A 400-600 word blog-style article rewriting the core insights. Written in Divya's voice: direct, real, motivational but not preachy.",
  "seo_keywords": ["8-12 long-tail keywords this episode could rank for"],
  "suggested_url_slug": "a-clean-url-slug-for-this-episode",
  "related_search_queries": [
    "What would someone Google before finding this episode?",
    "Another likely search query",
    "A third one"
  ],
  "content_format": "Interview | Solo monologue | Panel discussion | Q&A | Story-driven",
  "emotional_tone": "Motivational | Educational | Vulnerable | Casual | Intense | Reflective",
  "episode_quality_score": 7
}}"""


def chunk_transcript(text: str, max_chars: int = MAX_TRANSCRIPT_CHARS) -> list[str]:
    """Split long transcripts into chunks at paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def analyze_video(client: anthropic.Anthropic, video: dict, transcript: str) -> dict:
    """Send transcript to Claude and return structured analysis."""
    chunks = chunk_transcript(transcript)

    if len(chunks) == 1:
        prompt = ANALYSIS_PROMPT.format(
            transcript=transcript,
            title=video["title"],
            description=video.get("description", ""),
        )
    else:
        # For multi-chunk transcripts, send a merged summary request
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            prompt_chunk = (
                f"You are reading part {i+1}/{len(chunks)} of a podcast transcript "
                f"from 'The Divya Jain Podcast'. Title: {video['title']}\n\n"
                f"<transcript_part>\n{chunk}\n</transcript_part>\n\n"
                "Summarize the key points, topics, quotes, and takeaways from this section. "
                "Return a concise but thorough summary."
            )
            resp = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt_chunk}],
            )
            chunk_summaries.append(resp.content[0].text)
            time.sleep(0.5)

        merged = "\n\n---\n\n".join(chunk_summaries)
        prompt = ANALYSIS_PROMPT.format(
            transcript=f"[Merged summary of {len(chunks)} transcript segments]\n\n{merged}",
            title=video["title"],
            description=video.get("description", ""),
        )

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    return json.loads(text)


def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY in .env")
        sys.exit(1)

    metadata_path = RAW_DIR / "youtube_metadata.json"
    if not metadata_path.exists():
        print("ERROR: Run step1_youtube_metadata.py first.")
        sys.exit(1)

    with open(metadata_path) as f:
        videos = json.load(f)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Filter to videos that have transcripts and haven't been analyzed yet
    to_analyze = []
    for v in videos:
        vid = v["video_id"]
        txt_path = TRANSCRIPTS_DIR / f"{vid}.txt"
        analysis_path = ANALYSIS_YT_DIR / f"{vid}.json"
        if txt_path.exists() and not analysis_path.exists():
            to_analyze.append(v)

    print(f"{len(to_analyze)} videos to analyze ({len(videos) - len(to_analyze)} already done).\n")

    success, failed = 0, 0
    for video in tqdm(to_analyze, desc="Analyzing"):
        vid = video["video_id"]
        txt_path = TRANSCRIPTS_DIR / f"{vid}.txt"
        analysis_path = ANALYSIS_YT_DIR / f"{vid}.json"

        try:
            transcript = txt_path.read_text()
            analysis = analyze_video(client, video, transcript)
            with open(analysis_path, "w") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            success += 1
        except json.JSONDecodeError as e:
            print(f"\nJSON parse error for {vid}: {e}")
            failed += 1
        except anthropic.APIError as e:
            print(f"\nAPI error for {vid}: {e}")
            failed += 1
            time.sleep(5)  # back off on API errors
        except Exception as e:
            print(f"\nUnexpected error for {vid}: {e}")
            failed += 1

        time.sleep(1)  # rate limiting

    print(f"\nDone: {success} succeeded, {failed} failed.")


if __name__ == "__main__":
    main()
