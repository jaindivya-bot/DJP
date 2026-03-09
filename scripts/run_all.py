#!/usr/bin/env python3
"""
Master runner — execute the full audit pipeline in order.

Usage:
  python run_all.py              # Run all steps
  python run_all.py --from 3     # Resume from step 3
  python run_all.py --only 5 6   # Run only steps 5 and 6
"""

import argparse
import importlib
import sys
import time


STEPS = [
    ("step1_youtube_metadata", "Phase 1.1: YouTube Metadata Extraction"),
    ("step2_transcripts", "Phase 1.2: Transcript Extraction & Cleaning"),
    ("step3_analyze_youtube", "Phase 1.3: AI-Powered YouTube Analysis"),
    ("step4_youtube_master_db", "Phase 1.4: YouTube Master Database"),
    ("step5_instagram_extract", "Phase 2.1: Instagram Extraction"),
    ("step6_analyze_instagram", "Phase 2.3: Instagram Analysis + Master DB"),
    ("step7_cross_platform_audit", "Phase 3: Cross-Platform Audit"),
    ("step8_performance_scoring", "Phase 4: Performance Scoring"),
    ("step9_final_deliverables", "Phase 5: Final Deliverables"),
]


def main():
    parser = argparse.ArgumentParser(description="Run the Divya Jain Podcast content audit pipeline")
    parser.add_argument("--from", type=int, dest="from_step", help="Start from step N (1-indexed)")
    parser.add_argument("--only", type=int, nargs="+", help="Run only these step numbers")
    args = parser.parse_args()

    steps_to_run = list(range(len(STEPS)))

    if args.from_step:
        steps_to_run = [i for i in steps_to_run if i >= args.from_step - 1]
    if args.only:
        steps_to_run = [i - 1 for i in args.only if 1 <= i <= len(STEPS)]

    print("=" * 60)
    print("The Divya Jain Podcast — Content Audit Pipeline")
    print("=" * 60)

    for idx in steps_to_run:
        module_name, description = STEPS[idx]
        print(f"\n{'─' * 60}")
        print(f"  Step {idx + 1}/{len(STEPS)}: {description}")
        print(f"{'─' * 60}\n")

        try:
            module = importlib.import_module(module_name)
            module.main()
        except SystemExit:
            print(f"\nStep {idx + 1} exited (likely missing prerequisites). Stopping.")
            sys.exit(1)
        except Exception as e:
            print(f"\nStep {idx + 1} failed: {e}")
            print("You can resume with: python run_all.py --from", idx + 1)
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Pipeline complete! Check the databases/ and reports/ directories.")
    print("=" * 60)


if __name__ == "__main__":
    main()
