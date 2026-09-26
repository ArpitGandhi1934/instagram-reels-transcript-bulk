#!/usr/bin/env python3
"""Instagram Reels transcripts in bulk -> CSV or JSONL.

Calls the yugenox/instagram-scraper Actor on Apify with transcripts, Instagram's AI summary and
view counts turned on, then writes one row per reel: the hook (first sentence), the full
transcript, plays/views, likes, comments and the AI summary.

Usage:
    python reels_to_text.py --profile nasa --max 20
    python reels_to_text.py https://www.instagram.com/reel/<code>/ [...]
    python reels_to_text.py --audio 271328201351336 --max 30 --out sound.jsonl
    ...--out ends in .csv (default reels.csv) or .jsonl

Requires Python 3.10+, `pip install -r requirements.txt`, and APIFY_TOKEN in the environment
or in a .env file next to this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

from apify_client import ApifyClient

ACTOR = "yugenox/instagram-scraper"

COLUMNS = [
    "url", "owner", "owner_followers", "created_at", "duration_sec", "plays", "views", "likes",
    "comments", "transcript_status", "transcript_language", "hook", "transcript", "ai_title",
    "ai_summary", "caption", "audio",
]


def load_dotenv(path: Path = Path(__file__).with_name(".env")) -> None:
    """Minimal .env reader so the script has no extra dependency."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _field(run, camel: str, snake: str):
    """apify-client v1/v2 return dicts, v3 returns a model object. Support both."""
    return run[camel] if isinstance(run, dict) else getattr(run, snake)


def profile_reels_url(p: str) -> str:
    """'nasa', '@nasa' or a profile URL -> the profile's reels tab."""
    handle = re.sub(r"^https?://(www\.)?instagram\.com/", "", p).lstrip("@").split("/")[0]
    return f"https://www.instagram.com/{handle}/reels/"


def audio_url(a: str) -> str:
    return f"https://www.instagram.com/reels/audio/{a}/" if a.isdigit() else a


def hook(text: str | None) -> str:
    """The first sentence of the transcript (or its first 25 words if it has no punctuation)."""
    if not text:
        return ""
    t = re.sub(r"\s+", " ", text).strip()
    m = re.match(r"^(.+?[.!?。！？])(\s|$)", t)
    if m and len(m.group(1)) <= 300:
        return m.group(1)
    return " ".join(t.split(" ")[:25])


def transcript_status(r: dict) -> str:
    if not r.get("isVideo"):
        return "not a video"
    if r.get("transcript") == "":
        return "no speech found"
    if r.get("transcript") is None:
        return "not transcribed"
    return "ok"


def to_row(r: dict) -> dict:
    video = r.get("video") or {}
    owner = r.get("owner") or {}
    audio = r.get("audio") or {}
    duration = video.get("duration")
    return {
        "url": r.get("url"),
        "owner": owner.get("username"),
        "owner_followers": owner.get("followerCount"),
        "created_at": r.get("createdAt"),
        "duration_sec": round(duration) if isinstance(duration, (int, float)) else None,
        "plays": video.get("playCount"),
        "views": video.get("viewCount"),
        "likes": r.get("likeCount"),
        "comments": r.get("commentCount"),
        "transcript_status": transcript_status(r),
        "transcript_language": r.get("transcriptLanguage"),
        "hook": hook(r.get("transcript")),
        "transcript": r.get("transcript") or "",
        "ai_title": r.get("aiTitle"),
        "ai_summary": r.get("aiSummary"),
        "caption": r.get("caption"),
        "audio": " - ".join(x for x in (audio.get("title"), audio.get("artist")) if x) or None,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Instagram Reels transcripts in bulk to CSV/JSONL")
    p.add_argument("urls", nargs="*", help="reel or post URLs")
    p.add_argument("--profile", action="append", default=[], help="handle or profile URL (reels tab)")
    p.add_argument("--audio", action="append", default=[], help="audio id or audio page URL")
    p.add_argument("--file", help="text file with one Instagram URL per line")
    p.add_argument("--max", type=int, default=20, help="max reels for the whole run (default 20)")
    p.add_argument("--until", help='only reels newer than a date (YYYY-MM-DD) or period ("30 days")')
    p.add_argument("--out", default="reels.csv", help="output path, .csv or .jsonl")
    p.add_argument("--max-charge", type=float, default=1.0, help="cost cap for the run in USD")
    args = p.parse_args()

    urls = list(args.urls)
    urls += [profile_reels_url(x) for x in args.profile]
    urls += [audio_url(x) for x in args.audio]
    if args.file:
        lines = Path(args.file).read_text().splitlines()
        urls += [s.strip() for s in lines if s.strip() and not s.strip().startswith("#")]
    if not urls:
        p.error("give reel URLs, --profile <handle>, --audio <id> or --file urls.txt")

    load_dotenv()
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN (see .env.example)")

    run_input: dict = {
        "startUrls": urls,
        "maxItems": args.max,
        "includeTranscript": True,  # $0.004 per started minute; reels with no detectable speech are usually skipped
        "includeAiSummary": True,  # Instagram's own AI title + summary, included in the row price
        "includeVideoViews": True,  # adds video.viewCount next to video.playCount, included
    }
    if args.until:
        run_input["until"] = args.until

    client = ApifyClient(token)
    print(f"Running {ACTOR} ...", file=sys.stderr)
    # max_total_charge_usd caps what this run can cost you (pay-per-event Actors only).
    run = client.actor(ACTOR).call(
        run_input=run_input, max_total_charge_usd=Decimal(str(args.max_charge))
    )
    if run is None:
        sys.exit("The run did not finish")
    print(f"Run {_field(run, 'id', 'id')} finished: {_field(run, 'status', 'status')}", file=sys.stderr)

    items = client.dataset(_field(run, "defaultDatasetId", "default_dataset_id")).iterate_items()
    rows = [to_row(it) for it in items if it.get("dataType") == "post"]

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        if args.out.endswith(".jsonl"):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        else:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
    ok = sum(1 for r in rows if r["transcript_status"] == "ok")
    print(f"Wrote {len(rows)} reels ({ok} transcribed) to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
