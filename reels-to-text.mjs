#!/usr/bin/env node
// Instagram Reels transcripts in bulk -> CSV or JSONL.
//
// Calls the yugenox/instagram-scraper Actor on Apify with transcripts, Instagram's AI summary and
// view counts turned on, then writes one row per reel: the hook (first sentence), the full
// transcript, plays/views, likes, comments and the AI summary.
//
// Usage:
//   node --env-file=.env reels-to-text.mjs --profile nasa --max 20
//   node --env-file=.env reels-to-text.mjs https://www.instagram.com/reel/<code>/ [...]
//   node --env-file=.env reels-to-text.mjs --audio 271328201351336 --max 30 --out sound.jsonl
//   ...--out ends in .csv (default reels.csv) or .jsonl
//
// Requires Node 20.6+ and APIFY_TOKEN in the environment (or in .env).

import { writeFileSync, readFileSync } from 'node:fs';
import { ApifyClient } from 'apify-client';

const ACTOR = 'yugenox/instagram-scraper';

function parseArgs(argv) {
    const opts = { urls: [], max: 20, out: 'reels.csv', until: null, maxCharge: 1 };
    for (let i = 0; i < argv.length; i++) {
        const a = argv[i];
        if (a === '--profile') opts.urls.push(profileReelsUrl(argv[++i]));
        else if (a === '--audio') opts.urls.push(audioUrl(argv[++i]));
        else if (a === '--file') {
            const lines = readFileSync(argv[++i], 'utf8').split('\n').map((s) => s.trim());
            opts.urls.push(...lines.filter((s) => s && !s.startsWith('#')));
        } else if (a === '--max') opts.max = Number(argv[++i]);
        else if (a === '--until') opts.until = argv[++i];
        else if (a === '--out') opts.out = argv[++i];
        else if (a === '--max-charge') opts.maxCharge = Number(argv[++i]);
        else if (a.startsWith('--')) throw new Error(`Unknown option ${a}`);
        else opts.urls.push(a);
    }
    if (!opts.urls.length) throw new Error('Give reel URLs, --profile <handle>, --audio <id> or --file urls.txt');
    return opts;
}

// "nasa", "@nasa" or a profile URL -> the profile's reels tab
function profileReelsUrl(p) {
    const handle = p.replace(/^https?:\/\/(www\.)?instagram\.com\//, '').replace(/^@/, '').split('/')[0];
    return `https://www.instagram.com/${handle}/reels/`;
}

// "271328201351336" or an audio URL -> the audio page
function audioUrl(a) {
    return /^\d+$/.test(a) ? `https://www.instagram.com/reels/audio/${a}/` : a;
}

// The hook: the first sentence of the transcript (or its first 25 words if it has no punctuation).
function hook(text) {
    if (!text) return '';
    const t = text.replace(/\s+/g, ' ').trim();
    const m = t.match(/^(.+?[.!?。！？])(\s|$)/);
    if (m && m[1].length <= 300) return m[1];
    return t.split(' ').slice(0, 25).join(' ');
}

function transcriptStatus(r) {
    if (!r.isVideo) return 'not a video';
    if (r.transcript === '') return 'no speech found';
    if (r.transcript == null) return 'not transcribed';
    return 'ok';
}

function toRow(r) {
    return {
        url: r.url,
        owner: r.owner?.username,
        owner_followers: r.owner?.followerCount,
        created_at: r.createdAt,
        duration_sec: r.video?.duration != null ? Math.round(r.video.duration) : null,
        plays: r.video?.playCount,
        views: r.video?.viewCount,
        likes: r.likeCount,
        comments: r.commentCount,
        transcript_status: transcriptStatus(r),
        transcript_language: r.transcriptLanguage,
        hook: hook(r.transcript),
        transcript: r.transcript || '',
        ai_title: r.aiTitle,
        ai_summary: r.aiSummary,
        caption: r.caption,
        audio: r.audio ? [r.audio.title, r.audio.artist].filter(Boolean).join(' - ') : null,
    };
}

function csvCell(v) {
    if (v == null) return '';
    const s = String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

async function main() {
    const opts = parseArgs(process.argv.slice(2));
    if (!process.env.APIFY_TOKEN) throw new Error('Set APIFY_TOKEN (see .env.example)');

    const input = {
        startUrls: opts.urls,
        maxItems: opts.max,
        includeTranscript: true, // $0.004 per started minute; reels with no detectable speech are usually skipped
        includeAiSummary: true, // Instagram's own AI title + summary, included in the row price
        includeVideoViews: true, // adds video.viewCount next to video.playCount, included
    };
    if (opts.until) input.until = opts.until;

    const client = new ApifyClient({ token: process.env.APIFY_TOKEN });
    console.error(`Running ${ACTOR} ...`);
    // maxTotalChargeUsd caps what this run can cost you (pay-per-event Actors only).
    const run = await client.actor(ACTOR).call(input, { maxTotalChargeUsd: opts.maxCharge });
    console.error(`Run ${run.id} finished: ${run.status}`);

    const { items } = await client.dataset(run.defaultDatasetId).listItems();
    const rows = items.filter((it) => it.dataType === 'post').map(toRow);

    if (opts.out.endsWith('.jsonl')) {
        writeFileSync(opts.out, rows.map((r) => JSON.stringify(r)).join('\n') + (rows.length ? '\n' : ''));
    } else {
        const cols = Object.keys(toRow({}));
        const lines = [cols.join(','), ...rows.map((r) => cols.map((c) => csvCell(r[c])).join(','))];
        writeFileSync(opts.out, `${lines.join('\n')}\n`);
    }
    const ok = rows.filter((r) => r.transcript_status === 'ok').length;
    console.error(`Wrote ${rows.length} reels (${ok} transcribed) to ${opts.out}`);
}

main().catch((err) => {
    console.error(err.message);
    process.exit(1);
});
