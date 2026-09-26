# Instagram Reels Transcript in Bulk: Reels to Text (CSV / JSONL)

[![Instagram Scraper on Apify][badge-ig]][store-ig]

Get the **Instagram Reels transcript in bulk** for a whole profile, a list of reel URLs or every reel that uses a sound. Each row has the spoken text, the hook (first sentence), plays and views, likes, comments and Instagram's own AI summary, written to CSV or JSONL. The Node.js and Python scripts here call the [Instagram Scraper][store-ig] Actor on Apify. It works on public reels without an Instagram login, and transcripts cost $0.004 per started minute of audio.

## What you get

Real output from a test run on 2026-09-26 (`--profile mkbhd --max 3`, full rows in [`samples/profile-mkbhd.csv`](samples/profile-mkbhd.csv)):

| Reel | Length | Plays | Views | Likes | Hook (first sentence) | Instagram AI title |
|---|---:|---:|---:|---:|---|---|
| [DdRy_nDzZNS](https://www.instagram.com/reel/DdRy_nDzZNS/) | 40s | 2,269,553 | 1,037,562 | 76,288 | Okay, I'm not a designer, but I I do think that this has to be the greatest ruler ever made. | The Ruler That Redefines Accuracy: A Review and Analysis |
| [DdFHJkpyy58](https://www.instagram.com/reel/DdFHJkpyy58/) | 20s | 30,967,481 | 13,495,520 | 1,137,679 | Okay, so like it shows here and if I open it, it also shows, right? | Improve Your Space with Modern TV Setup Solutions for Home Decor |
| [DdB_gwDzaT8](https://www.instagram.com/reel/DdB_gwDzaT8/) | 82s | 76,823 | 43,057 | 1,837 | Hey Benny. | Cute Robot Camera Spins Around in a Self-Balancing Dance |

That run cost $0.0217: 3 rows at $0.0019 plus 4 started transcript minutes at $0.004 (40 s and 20 s are one minute each, 82 s is two).

Columns (CSV) or keys (JSONL):

| Column | Meaning |
|---|---|
| `url`, `owner`, `owner_followers`, `created_at` | The reel and who posted it |
| `duration_sec` | Video length |
| `plays`, `views` | Instagram's play count and its separate "views" metric (see [Limits](#limits)) |
| `likes`, `comments` | Public counts |
| `transcript_status` | `ok`, `no speech found`, `not transcribed` or `not a video` |
| `transcript_language` | Detected language code, e.g. `en` |
| `hook` | First sentence of the transcript (or its first 25 words) |
| `transcript` | Full speech-to-text, any language |
| `ai_title`, `ai_summary` | Instagram's own AI-written title and summary of the post, when it has one |
| `caption`, `audio` | Post caption and the sound it uses |

More samples: [`samples/reel-urls.csv`](samples/reel-urls.csv) (two reel URLs), [`samples/profile-nasa.jsonl`](samples/profile-nasa.jsonl) (includes a reel with no speech) and [`samples/audio-nasaadmin.jsonl`](samples/audio-nasaadmin.jsonl) (audio page).

## Quick start

1. Create a free Apify account and copy your API token ([sign up][signup], then Console > Settings > API & Integrations).
2. `cp .env.example .env` and paste the token after `APIFY_TOKEN=`.

**Node.js** (20.6 or newer):

```bash
npm install
node --env-file=.env reels-to-text.mjs --profile mkbhd --max 20
node --env-file=.env reels-to-text.mjs https://www.instagram.com/reel/DdPsDCWRT-u/ --out reels.jsonl
node --env-file=.env reels-to-text.mjs --audio 29369820619287776 --max 30 --out sound.csv
```

**Python** (3.10 or newer):

```bash
pip install -r requirements.txt
python reels_to_text.py --profile mkbhd --max 20
python reels_to_text.py --file reels.example.txt --out reels.jsonl
python reels_to_text.py --audio 29369820619287776 --max 30 --until "30 days"
```

| Option | What it does | Default |
|---|---|---|
| reel URLs | `/reel/<code>/`, `/p/<code>/` or `/share/` links | |
| `--profile <handle>` | A handle, `@handle` or profile URL; reads the profile's reels tab, newest first | |
| `--audio <id>` | An audio id or `/reels/audio/<id>/` URL; reels that use that sound | |
| `--file urls.txt` | One URL per line, any of the above | |
| `--max N` | Maximum reels for the whole run | `20` |
| `--until` | Only reels newer than a date (`2026-09-01`) or a period (`30 days`, `2 weeks`). Profile reading stops at the first older reel, so you don't pay for older ones | |
| `--out` | `.csv` or `.jsonl` | `reels.csv` |
| `--max-charge USD` | Hard cost cap for the run, enforced by Apify | `1` |

Find the hooks of a creator's best-performing reels:

```bash
jq -r 'select(.plays and .hook != "") | [.plays, .hook] | @tsv' reels.jsonl | sort -rn | head -20
```

## What people use it for

- **Hook and script research.** Pull the last 50 reels of the top accounts in a niche and read what the first sentence says on the reels with the most plays.
- **Repurposing your own reels** into blog posts, captions, newsletters or YouTube scripts.
- **Feeding an LLM.** JSONL with transcript, AI summary and engagement drops straight into a RAG index or a prompt.
- **Trend checks on a sound.** What are people saying in the reels that use a trending audio?

## Price

Pay per result, no subscription. Prices checked on 2026-09-26 from the Apify Store (Apify Free plan price):

| Option | Per reel row | Transcript | One 30-second reel, all-in | 1,000 such reels |
|---|---:|---:|---:|---:|
| **[yugenox/instagram-scraper][store-ig]** (this repo) | $0.0019 | $0.004 per started minute | **$0.0059** | **$5.90** |
| apify/instagram-reel-scraper | $0.0026 | $0.048 per started minute | $0.0506 | $50.60 |
| sian.agency/instagram-ai-transcript-extractor | | $0.028 per transcribed reel | $0.028 | $28.00 |

Our row price already includes Instagram's AI summary, the views count and the latest comments. Apify's free plan includes monthly credit you can spend on this, but free-plan runs of this Actor are currently limited to 10 results each. Other Actors in the table also charge small per-run start fees.

## Why this instead of the Instagram Graph API

The official Instagram Graph API is the right tool for publishing to, and reading insights of, professional accounts you manage. For reading other people's reels as text it doesn't help:

- **Only accounts that authorized your app.** The Graph API returns media for Instagram professional accounts connected to your app. Business Discovery adds a few public fields of other business and creator accounts, but not transcripts.
- **No transcript field.** You would download each video and run speech-to-text yourself.
- **Setup and review.** You need a Meta developer app, an Instagram professional account, access tokens and, for most permissions, app review. The older Instagram Basic Display API was shut down on December 4, 2024.

Here you need one Apify token.

## Limits

- **Public reels only.** Private accounts are skipped. Nothing here signs in to Instagram.
- **Plays and views are not verified counts.** `plays` (`video.playCount`) and `views` (`video.viewCount`) are two different Instagram metrics, read logged-out. They can differ from what the creator sees in Insights, so don't use them to settle creator payouts. Plays come from the profile's reels tab, so single reel URLs usually have views but no plays.
- **Transcripts** cover videos up to 15 minutes; longer ones are skipped at no charge. Reels set to a licensed song are skipped and not charged. Other videos are transcribed and billed per started minute even if they turn out to have no speech (`no speech found`). A song uploaded as someone's "original audio" is transcribed as lyrics.
- **Search limits.** If you pass hashtag or keyword pages instead, Instagram shows logged-out visitors a curated set of top posts, about 60 per term. Comments come newest first and don't include replies.
- The AI title and summary exist only when Instagram has generated one for that post.

## More

- Every input mode of the Instagram and YouTube scrapers in Node, Python, curl, Apify CLI and Google Sheets: [youtube-instagram-scraper-examples](https://github.com/ArpitGandhi1934/youtube-instagram-scraper-examples)
- YouTube dislike counts in bulk: [youtube-dislike-count-bulk](https://github.com/ArpitGandhi1934/youtube-dislike-count-bulk)
- Guides on [yugenox-data.vercel.app](https://yugenox-data.vercel.app): [Instagram Reels transcripts](https://yugenox-data.vercel.app/instagram/reels-transcripts), [reel transcript tools compared](https://yugenox-data.vercel.app/compare/instagram-reel-transcript-tools), [reels by audio](https://yugenox-data.vercel.app/instagram/reels-by-audio), [pricing calculator](https://yugenox-data.vercel.app/pricing-calculator)
- The Actor itself, with its input form, output schema and reviews: [Instagram Scraper on Apify][store-ig]. Other ways to call it (clients, OpenAPI, MCP for AI agents) are on its [API page][api-ig].

## Legal

- Not affiliated with Instagram or Meta. Instagram is a trademark of Meta Platforms, Inc.
- The Actor collects publicly available data only. Usernames, captions and transcripts of people's speech can be personal data; follow GDPR, PIPEDA, CCPA and Instagram's terms when you store or publish results, and respect creators' copyright when you reuse their words. See [Is web scraping legal?][legal].
- Input keys verified against the Actor's input schema on 2026-09-26 (build 0.2.7).
- MIT licensed. Made by Yugenox Corporation.

<!-- All apify.com links for this README live below. When the Apify affiliate id exists, append ?fpr=<id> to these URLs only. -->
[store-ig]: https://apify.com/yugenox/instagram-scraper
[api-ig]: https://apify.com/yugenox/instagram-scraper/api
[badge-ig]: https://apify.com/actor-badge?actor=yugenox/instagram-scraper
[signup]: https://console.apify.com/sign-up
[legal]: https://blog.apify.com/is-web-scraping-legal/
