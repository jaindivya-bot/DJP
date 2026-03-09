"""Shared configuration and paths for the audit pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
INSTAGRAM_HANDLE = os.getenv("INSTAGRAM_HANDLE", "thedivyajainpodcast")
INSTAGRAM_EXPORT_PATH = os.getenv("INSTAGRAM_EXPORT_PATH", "")
KEYWORD_VOLUME_CSV_PATH = os.getenv("KEYWORD_VOLUME_CSV_PATH", "")

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent / "divyajainpodcast-audit"
RAW_DIR = BASE_DIR / "raw"
TRANSCRIPTS_DIR = RAW_DIR / "transcripts"
ANALYSIS_YT_DIR = BASE_DIR / "analysis" / "youtube"
ANALYSIS_IG_DIR = BASE_DIR / "analysis" / "instagram"
DATABASES_DIR = BASE_DIR / "databases"
REPORTS_DIR = BASE_DIR / "reports"

# Ensure directories exist
for d in [RAW_DIR, TRANSCRIPTS_DIR, ANALYSIS_YT_DIR, ANALYSIS_IG_DIR, DATABASES_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────
CONTENT_PILLARS = ["Business", "Education", "Health", "Spirituality", "Mixed"]
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANALYSIS_BATCH_SIZE = 10
MAX_TRANSCRIPT_CHARS = 80000  # chunk long transcripts if they exceed this
