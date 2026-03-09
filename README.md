# The Divya Jain Podcast — Content Audit & pSEO Pipeline

A complete pipeline to extract, analyze, and audit all content from **The Divya Jain Podcast** across YouTube and Instagram, producing structured data for a programmatic SEO (pSEO) website.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Edit .env with your YouTube API key, Anthropic API key, etc.

# 3. Run the full pipeline
cd scripts
python run_all.py

# Or run individual steps
python step1_youtube_metadata.py
python step2_transcripts.py
python step3_analyze_youtube.py
# ... etc.

# Resume from a specific step
python run_all.py --from 3

# Run only specific steps
python run_all.py --only 7 8 9
```

## Pipeline Steps

| Step | Script | Description |
|------|--------|-------------|
| 1 | `step1_youtube_metadata.py` | Extract video metadata via YouTube API or yt-dlp |
| 2 | `step2_transcripts.py` | Download and clean transcripts for every video |
| 3 | `step3_analyze_youtube.py` | AI analysis of each transcript (topics, takeaways, SEO keywords, blog rewrites) |
| 4 | `step4_youtube_master_db.py` | Compile YouTube master database CSV |
| 5 | `step5_instagram_extract.py` | Extract Instagram posts (data export or instaloader) |
| 6 | `step6_analyze_instagram.py` | AI analysis of Instagram posts + master database |
| 7 | `step7_cross_platform_audit.py` | Merge databases, topic clustering, gap analysis, guest directory |
| 8 | `step8_performance_scoring.py` | Performance scoring and evergreen/timely classification |
| 9 | `step9_final_deliverables.py` | Generate pSEO page plan and editorial calendar |

## Required API Keys

- **YouTube Data API v3** — Get one at [Google Cloud Console](https://console.cloud.google.com). Alternatively, install `yt-dlp` for API-free extraction.
- **Anthropic API** — For AI-powered content analysis (steps 3 and 6).
- **Instagram** — Either use Instagram's official data export (Settings → Download Your Information) or install `instaloader`.

## Output Structure

```
divyajainpodcast-audit/
├── raw/
│   ├── youtube_metadata.json
│   ├── instagram_export.json
│   └── transcripts/
│       ├── {video_id}.txt          # Cleaned plain text
│       └── {video_id}.json         # Timestamped segments
├── analysis/
│   ├── youtube/{video_id}.json     # Per-video AI analysis
│   └── instagram/{post_id}.json    # Per-post AI analysis
├── databases/
│   ├── youtube_master_database.csv
│   ├── instagram_master_database.csv
│   ├── unified_content_index.csv
│   ├── topic_clusters.json
│   ├── guest_directory.csv
│   ├── gap_analysis.csv
│   ├── content_performance_rankings.csv
│   └── pseo_page_plan.csv
└── reports/
    └── editorial_calendar_suggestions.csv
```

## Configuration

All settings are in `scripts/config.py` and `.env`. Key settings:

- `CLAUDE_MODEL` — Which Claude model to use for analysis (default: claude-sonnet-4-20250514)
- `ANALYSIS_BATCH_SIZE` — How many items to process per batch
- `MAX_TRANSCRIPT_CHARS` — Threshold for chunking long transcripts
