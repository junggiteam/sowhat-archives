"""Build the short editorial content shared by standalone pages and RSS."""
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
import json
import re

KST = timezone(timedelta(hours=9))
EARLY_SUMMARIES = Path(__file__).with_name('data') / 'sowhat_early_summaries.json'


def published_at(item: dict, entry: dict) -> datetime | None:
    for value in (item.get('publishedAt'), entry.get('publishedAt')):
        if not isinstance(value, str) or 'T' not in value:
            continue
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            continue
        if parsed.tzinfo is not None and parsed.astimezone(KST).date().isoformat() == item['date']:
            return parsed.astimezone(KST)
    return None


def short_excerpt(text: str, limit: int = 140) -> str:
    text = ' '.join(text.split())
    sentence = re.split(r'(?<=[.!?])\s+', text, maxsplit=1)[0]
    if len(sentence) <= limit:
        return sentence
    return sentence[:limit].rsplit(' ', 1)[0].rstrip(' ,…') + '…'


def collect(items: list[dict], cache: dict) -> dict:
    early = json.loads(EARLY_SUMMARIES.read_text(encoding='utf-8'))
    entries = cache.get('issues', {})
    summaries = {}
    used_volumes = set()
    for item in items:
        volume = item.get('volume')
        if not isinstance(volume, int) or volume < 1:
            continue
        entry = entries.get(item['id'], {})
        stories = [section for section in entry.get('sections', []) if section['headline'].strip()]
        introduction = early.get(item['id'], '')
        if not stories and not introduction:
            continue
        if volume in used_volumes:
            raise ValueError(f'Multiple publications would share letters/{volume}/')
        used_volumes.add(volume)
        summaries[item['id']] = {
            'introduction': introduction,
            'stories': [(s['cat'], s['headline'], short_excerpt(s['excerpt'])) for s in stories],
        }
    return summaries


def body(summary: dict) -> str:
    introduction = summary['introduction']
    intro_html = f'<p>{escape(introduction)}</p>' if introduction else ''
    rows = []
    for category, headline, excerpt in summary['stories']:
        text = f'<p>{escape(excerpt)}</p>' if excerpt and excerpt != headline else ''
        rows.append(f'<li><strong>{escape(category)} · {escape(headline)}</strong>{text}</li>')
    return intro_html + (f'<ul>{"".join(rows)}</ul>' if rows else '')
