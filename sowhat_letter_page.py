"""Issue summary page (/letters/<vol>/) in the archive's own look.

Layout (PC): top bar "← 모아보기로 가기" + date/weather, hero (issue no. · date, title,
three-line summary, "이번 호 전체 읽기" button) beside the cover image, story cards,
the eight topic links, then next/previous issue buttons. Mobile stacks the same order.
"""
from html import escape
from pathlib import Path
import json
import re

import sowhat_sections
import sowhat_summaries

ROOT = Path(__file__).resolve().parent
SITE = 'https://sowhat.bestexit.co.kr/'
INTROS = ROOT / 'data' / 'sowhat_summary_intros.json'  # hand-written summaries override the generated one
FIRST_NAV_VOLUME = sowhat_sections.MIN_VOLUME  # summaries navigated from Vol. 16 (current section layout)
SAY = {'TAX': '세무'}  # how a label reads inside a sentence

ARROW_L = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>'
ARROW_R = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'


def letter_url(item: dict) -> str:
    return f'{SITE}letters/{item["volume"]}/'


def navigable(items: list[dict], summaries: dict) -> list[dict]:
    """Published issues that have a summary page, newest first, from Vol. 16."""
    rows = [x for x in items if x['id'] in summaries and isinstance(x.get('volume'), int) and x['volume'] >= FIRST_NAV_VOLUME]
    return sorted(rows, key=lambda x: (x['date'], x['volume']), reverse=True)


def latest_url(items: list[dict], summaries: dict) -> str:
    rows = navigable(items, summaries)
    return letter_url(rows[0]) if rows else SITE


def latest_issue(items: list[dict]) -> dict | None:
    """Newest published issue whose sections are extracted (Vol. 16 onward) = newest summary page."""
    with_sections = {k for k, e in sowhat_sections.load_cache().get('issues', {}).items() if e.get('sections')}
    rows = [x for x in items if (x.get('volume') or 0) >= FIRST_NAV_VOLUME and x['id'] in with_sections]
    return max(rows, key=lambda x: (x['date'], x['volume'])) if rows else None


def fill_template(template: str, items: list[dict]) -> str:
    latest = latest_issue(items)
    return (template.replace('__LATEST_URL__', letter_url(latest) if latest else SITE)
                    .replace('__LATEST_VOL__', str(latest['volume']) if latest else ''))


def _first_sentence(text: str, limit: int = 110) -> str:
    text = ' '.join(text.split())
    sentence = re.split(r'(?<=[.!?요다])\s+', text, maxsplit=1)[0]
    if len(sentence) > limit:
        sentence = sentence[:limit].rsplit(' ', 1)[0].rstrip(' ,…') + '…'
    return sentence


def intro_lines(item: dict, sections: list[dict], early: str = '') -> list[str]:
    """Three short lines under the title: the lead story, the topics covered, a closing line."""
    try:
        manual = json.loads(INTROS.read_text(encoding='utf-8')).get(str(item['volume']))
    except FileNotFoundError:
        manual = None
    if manual:
        return manual if isinstance(manual, list) else [manual]
    if early:
        return [early]
    if not sections:
        return []
    lead = next((s for s in sections if s['headline'] == item['title']), sections[0])
    first = _first_sentence(lead.get('excerpt') or lead['headline'])
    order = [label for label, _, _ in sowhat_sections.CATEGORIES]
    cats = [SAY.get(c, c) for c in order if any(s['cat'] == c for s in sections)]
    if len(cats) >= 4:
        topics = f'{"·".join(cats[:3])}부터 {"·".join(cats[3:])}까지,'
    elif len(cats) >= 2:
        topics = f'{"·".join(cats)}까지,'
    else:
        topics = f'{cats[0]} 소식을 중심으로,'
    return [first, topics, '이번 호에서 다룬 핵심 내용을 모았습니다.']


def render(item: dict, entry: dict, early: str, newer: dict | None, older: dict | None,
           head: str, template: str, archive_css: str, letter_css: str, archive_js: str) -> str:
    vol = item['volume']
    sections = [s for s in entry.get('sections', []) if s.get('headline', '').strip()]
    top = re.search(r'<div class="swa-wrap"><header class="swa-top">.*?</header></div>', template, re.S).group(0)
    top = re.sub(r'<a class="swa-brand"[^>]*>.*?</a>',
                 f'<a class="swa-brand swa-letter-back" href="{SITE}">{ARROW_L}<span class="swa-brand-context">모아보기로 가기</span></a>', top, flags=re.S)
    footer = re.search(r'<div class="swa-wrap"><footer class="swa-footer[^"]*">.*?</footer></div>', template, re.S).group(0).replace('src="/assets/', f'src="{SITE}assets/')
    totop = re.search(r'<a class="swa-totop".*?</a>', template, re.S).group(0)

    lines = intro_lines(item, sections, early)
    intro = ''.join(f'<span>{escape(line)}</span>' for line in lines)
    image = item.get('image', '')
    cover = (f'<div class="swa-letter-cover"><img src="{escape(image, quote=True)}" alt="" width="630" height="360" decoding="async"></div>'
             if image else '')
    hero = (f'<section class="swa-letter-hero{" no-cover" if not image else ""}">'
            f'<div class="swa-letter-text"><p class="swa-letter-meta"><span class="swa-letter-vol">Vol. {str(vol).zfill(3)}</span>'
            f'<time datetime="{item["date"]}">{item["date"].replace("-", ".")}</time></p>'
            f'<h1>{escape(item["title"])}</h1>'
            + (f'<p class="swa-letter-intro">{intro}</p>' if intro else '') +
            f'<a class="swa-letter-read" href="{escape(item["url"], quote=True)}" target="_blank" rel="noopener">이번 호 전체 읽기{ARROW_R}</a></div>'
            f'{cover}</section>')

    slugs = {label: slug for label, slug, _ in sowhat_sections.CATEGORIES}
    cards = []
    for s in sections:
        slug = slugs.get(s['cat'])
        link = (sowhat_sections.issue_url(vol, slug, s.get('n', 1))
                if slug and sowhat_sections.issue_path(vol).exists() else item['url'])
        thumb = (f'<span class="swa-story-thumb"><img src="{escape(s["image"], quote=True)}" alt="" width="380" height="217" loading="lazy" decoding="async"></span>'
                 if s.get('image') else '')
        cards.append(f'<li class="swa-story"><a href="{escape(link, quote=True)}" target="_blank" rel="noopener">{thumb}'
                     f'<span class="swa-story-body"><span class="swa-story-cat">{escape(s["cat"])}</span>'
                     f'<strong class="swa-story-h">{escape(s["headline"])}</strong>'
                     + (f'<span class="swa-story-x">{escape(sowhat_summaries.short_excerpt(s["excerpt"]))}</span>' if s.get('excerpt') and sowhat_summaries.short_excerpt(s['excerpt']) != s['headline'] else '') +
                     '</span></a></li>')
    stories = (f'<section class="swa-letter-stories" aria-labelledby="swa-stories-h"><h2 id="swa-stories-h">이번 호 기사</h2>'
               f'<ol class="swa-story-grid">{"".join(cards)}</ol></section>') if cards else ''

    topics = ''.join(f'<a class="swa-topic" href="{SITE}category/{slug}/">{escape(label)}</a>' for label, slug, _ in sowhat_sections.CATEGORIES)
    topic_box = (f'<section class="swa-letter-topics" aria-labelledby="swa-topics-h"><h2 id="swa-topics-h">주제별 뉴스레터 모아보기</h2>'
                 f'<nav class="swa-topic-grid" aria-label="주제별 뉴스레터">{topics}</nav></section>')

    left = (f'<a class="swa-issue-btn is-newer" href="{letter_url(newer)}" aria-label="다음호 요약 보기, Vol. {newer["volume"]}">{ARROW_L}다음호 요약 보기</a>'
            if newer else '<span class="swa-issue-slot" aria-hidden="true"></span>')
    right = (f'<a class="swa-issue-btn is-older" href="{letter_url(older)}" aria-label="이전호 요약 보기, Vol. {older["volume"]}">이전호 요약 보기{ARROW_R}</a>'
             if older else '<span class="swa-issue-slot" aria-hidden="true"></span>')
    pager = f'<nav class="swa-issue-pager" aria-label="다른 호 요약">{left}{right}</nav>' if (newer or older) else ''

    body = (f'<div id="sowhat-archive" class="swa-letter" data-archive-base="{SITE}">' + top +
            f'<main class="swa-wrap swa-letter-main">{hero}{stories}{topic_box}{pager}</main>' + footer + totop + '</div>')
    return head + '<style>\n' + archive_css + letter_css + '\n</style>\n' + body + '\n<script>\n' + archive_js + '\n</script>\n</body></html>\n'
