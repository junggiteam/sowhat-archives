"""Build a static, crawlable archive for sowhat.bestexit.co.kr.

The public upstream manifest is shared with the Imweb widget. Scheduled builds
refresh the initial HTML as well, so new cards do not depend on JavaScript for
discovery by search engines. No account tokens or subscriber data are required.
"""
from pathlib import Path
from html import escape
from collections import Counter
from datetime import timedelta, datetime, timezone
from email.utils import format_datetime
import argparse
import re
import json
import time
import urllib.request
from xml.etree.ElementTree import Element, ParseError, SubElement, fromstring, register_namespace, tostring

from build_sowhat_widget import build, render_widget, month_name, month_url
import sowhat_sections
import sowhat_summaries
import sowhat_letter_page
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
CANONICAL = 'https://sowhat.bestexit.co.kr/'
UPSTREAM = 'https://raw.githubusercontent.com/junggiteam/naver-news/main/data/sowhat_archive.json'
VERIFICATION = json.loads((ROOT / 'site-verification.json').read_text(encoding='utf-8'))
ATOM_NS = 'http://www.w3.org/2005/Atom'
register_namespace('atom', ATOM_NS)


def refresh() -> None:
    request = urllib.request.Request(UPSTREAM + '?v=' + str(int(time.time() // 300)), headers={'User-Agent':'BestExit-SoWhatSite/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            if payload.get('schemaVersion') != 1 or payload.get('source') != 'https://page.stibee.com/archives/479387' or not payload.get('items'):
                raise ValueError('Invalid public archive manifest')
            for item in payload['items']:
                if not item.get('title') or not item.get('url','').startswith('https://stib.ee/'):
                    raise ValueError('Invalid publication')
            destination = ROOT / 'data/sowhat_archive.json'
            destination.parent.mkdir(exist_ok=True)
            temporary = destination.with_suffix('.tmp')
            temporary.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            temporary.replace(destination)
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


# Search result snippet for the main page (Google/Naver); also the site name shown above the title is '쏘왓레터'.
SITE_DESCRIPTION = '쏘왓레터는 경제 흐름과 기업 경영에 필요한 M&A·기업승계·세무 이슈를 정리하는 중기이코노미의 경제·경영 뉴스레터입니다.'


def page_title(archive_month: str) -> str:
    if archive_month:
        return month_name(archive_month) + ' 경제·경영 뉴스레터 모아보기 | 쏘왓레터'
    return '중기이코노미 쏘왓레터 | 경제 뉴스레터·경영 뉴스레터'


def page_head(title, description, canonical, share_title, share_description, graph, *, share_image='', article=False):
    structured = json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('<','\\u003c')
    image = escape(share_image or CANONICAL+'assets/sowhat-og-v4.png', quote=True)
    image_details = '' if share_image else ('<meta property="og:image:width" content="1200">\n'
                                            '<meta property="og:image:height" content="630">\n'
                                            '<meta property="og:image:alt" content="결론이 있는 뉴스레터, 중기이코노미 쏘왓레터">')
    head = f'''<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description,quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="naver-site-verification" content="{escape(VERIFICATION['naver'],quote=True)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/favicon.ico?v=2" sizes="48x48">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg?v=2">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/favicon-192.png?v=2">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png?v=2">
<link rel="alternate" type="application/rss+xml" title="쏘왓레터" href="https://sowhat.bestexit.co.kr/rss.xml">
<link rel="preconnect" href="https://img2.stibee.com">
<link rel="dns-prefetch" href="https://raw.githubusercontent.com">
<meta property="og:type" content="{'article' if article else 'website'}">
<meta property="og:locale" content="ko_KR">
<meta property="og:site_name" content="쏘왓레터">
<meta property="og:title" content="{escape(share_title,quote=True)}">
<meta property="og:description" content="{escape(share_description,quote=True)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}">
{image_details}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(share_title,quote=True)}">
<meta name="twitter:description" content="{escape(share_description,quote=True)}">
<meta name="twitter:image" content="{image}">
<meta name="theme-color" content="#d12f30">
<script type="application/ld+json">{structured}</script>
<style>body{{margin:0;background:#fff}}</style>
</head><body>'''
    return head


def render_page(payload: dict, archive_month: str = '') -> str:
    items = [x for x in payload['items'] if not archive_month or x['date'].startswith(archive_month)]
    canonical = month_url(archive_month)
    title = page_title(archive_month)
    description = (f'{month_name(archive_month)} 경제·경영 뉴스레터 쏘왓레터 {len(items)}개 발행호를 모았습니다. ' if archive_month else '') + ('대표이미지와 제목으로 지난 발행호를 찾고 원문 읽기와 구독 신청을 할 수 있습니다.' if archive_month else SITE_DESCRIPTION)
    graph = [
        {'@type':'WebSite','@id':CANONICAL+'#website','url':CANONICAL,'name':'쏘왓레터','alternateName':['중기이코노미 쏘왓레터','쏘왓레터 모아보기','SO WHAT'],'description':SITE_DESCRIPTION,'inLanguage':'ko-KR','publisher':{'@type':'Organization','name':'중기이코노미'}},
    ]
    if archive_month:
        graph.append({'@type':'BreadcrumbList','itemListElement':[
            {'@type':'ListItem','position':1,'name':'쏘왓레터 모아보기','item':CANONICAL},
            {'@type':'ListItem','position':2,'name':month_name(archive_month),'item':canonical},
        ]})
    # Link previews (KakaoTalk, SNS) use brand copy on the main page; search title/description stay keyword-focused.
    share_title = title if archive_month else '결론이 있는 뉴스레터, 중기이코노미 쏘왓레터'
    share_description = description if archive_month else '복잡한 정보는 덜어내고 방향성 있는 결론만 전달하는 쏘왓레터를 구독해보세요'
    head = page_head(title, description, canonical, share_title, share_description, graph)
    return head + render_widget(payload['items'], archive_month) + '</body></html>\n'


def category_url(slug: str) -> str:
    return CANONICAL + 'category/' + slug + '/'


def render_category_page(payload: dict, cache: dict, label: str) -> str:
    """One category (e.g. M&A): each issue's section for it, newest first."""
    slug, intro = next((s2, i) for l, s2, i in sowhat_sections.CATEGORIES if l == label)
    rows = sowhat_sections.by_category(payload['items'], cache)[label]
    canonical = category_url(slug)
    # search title: the "○○ 뉴스레터" keyword first, then a second search phrase
    topic_title = {
        'company': '기업 뉴스레터 · 기업 경영 이슈 모아보기',
        'finance': '금융 뉴스레터 · 금리·대출 동향 모아보기',
        'invest': '투자 뉴스레터 · 증시·투자 흐름 모아보기',
        'ma': 'M&A 뉴스레터 · 인수합병 동향 모아보기',
        'ipo': 'IPO 뉴스레터 · 상장·공모주 흐름 모아보기',
        'succession': '기업승계 뉴스레터 · 가업승계 모아보기',
        'tax': '세무 뉴스레터 · 기업 세무·절세 모아보기',
        'wealth': '재테크 뉴스레터 · 자산관리·절세 모아보기',
    }.get(slug, f'{label} 뉴스레터 모아보기')
    title = f'{topic_title} | 쏘왓레터'
    description = f'{intro} 중기이코노미 쏘왓레터에서 발행한 글을 최신순으로 읽어보세요.'
    graph = [
        {'@type':'WebSite','@id':CANONICAL+'#website','url':CANONICAL,'name':'쏘왓레터','inLanguage':'ko-KR','publisher':{'@type':'Organization','name':'중기이코노미'}},
        {'@type':'BreadcrumbList','itemListElement':[
            {'@type':'ListItem','position':1,'name':'쏘왓레터 모아보기','item':CANONICAL},
            {'@type':'ListItem','position':2,'name':f'{label} 뉴스레터','item':canonical},
        ]},
        {'@type':'CollectionPage','@id':canonical+'#list','name':topic_title,'url':canonical,'inLanguage':'ko-KR','isPartOf':{'@id':CANONICAL+'#website'},
         'mainEntity':{'@type':'ItemList','numberOfItems':len(rows),'itemListElement':[{'@type':'ListItem','position':n+1,'item':{'@type':'CreativeWork','name':sec['headline'],'url':it['url'],'datePublished':it['date']}} for n,(it,sec) in enumerate(rows)]}},
    ]
    head = page_head(title, description, canonical, title, description, graph)
    template = sowhat_letter_page.fill_template((ROOT / 'widgets/sowhat-archive-template.html').read_text(encoding='utf-8'), payload['items'])
    top = re.search(r'<div class="swa-wrap"><header class="swa-top">.*?</header></div>', template, re.S).group(0)
    footer = re.search(r'<div class="swa-wrap"><footer class="swa-footer[^"]*">.*?</footer></div>', template, re.S).group(0).replace('src="/assets/', 'src="'+CANONICAL+'assets/')
    totop = re.search(r'<a class="swa-totop".*?</a>', template, re.S).group(0)
    tabs = ''.join(f'<a class="swa-cat-tab" href="{category_url(s2)}"' + (' aria-current="page"' if l == label else '') + f'>{escape(l)}</a>' for l, s2, _ in sowhat_sections.CATEGORIES)
    items_html = []
    for it, sec in rows:
        link = (sowhat_sections.issue_url(it['volume'], slug, sec.get('n', 1)) if sowhat_sections.issue_path(it['volume']).exists()
                else it['url'] + '#:~:text=' + quote(sec['headline'], safe=''))
        thumb = (f'<img src="{escape(sec["image"],quote=True)}" alt="" width="380" height="217" loading="lazy" decoding="async">' if sec['image']
                 else f'<span class="swa-cat-ph">{escape(label)}</span>')
        items_html.append(
            f'<li class="swa-cat-row"><a href="{escape(link,quote=True)}" target="_blank" rel="noopener" aria-label="{escape(sec["headline"],quote=True)} — Vol. {it["volume"]} 쏘왓레터 본문 새 창">'
            f'<span class="swa-cat-when"><b>{it["date"][5:].replace("-",".")}</b><span>Vol. {str(it["volume"]).zfill(3)}</span></span>'
            f'<span class="swa-cat-body"><strong class="swa-cat-h">{escape(sec["headline"])}</strong><span class="swa-cat-x">{escape(sec["excerpt"])}</span></span>'
            f'<span class="swa-cat-thumb">{thumb}</span></a></li>')
    body = (f'<div id="sowhat-archive" class="swa-category" data-archive-base="{CANONICAL}">' + top +
            '<main class="swa-wrap swa-cat">'
            f'<div class="swa-cat-hero"><div><h1><em>{escape(label)}</em> 뉴스레터 모아보기</h1><p>{escape(intro)}</p></div><p class="swa-cat-count">{len(rows)}건 · 최신순</p></div>'
            f'<nav class="swa-cat-tabs" aria-label="카테고리">{tabs}</nav>'
            f'<ol class="swa-cat-list" data-swa-cat-list>{"".join(items_html)}</ol>'
            '<div class="swa-bottom swa-cat-end" data-swa-cat-bottom><button class="swa-more" type="button" data-swa-cat-more hidden>지난 글 <span class="swa-more-accent">더 보기 +</span></button>'
            f'<a class="swa-cat-home" href="{CANONICAL}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>쏘왓레터 모아보기</a></div>'
            '</main>' + footer + totop + f'<a class="swa-cat-back" href="{CANONICAL}" data-swa-cat-back><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>쏘왓레터 모아보기로 가기</a>' + '</div>')
    css = (ROOT / 'widgets/sowhat-archive.css').read_text(encoding='utf-8') + (ROOT / 'widgets/sowhat-category.css').read_text(encoding='utf-8')
    js = (ROOT / 'widgets/sowhat-archive.js').read_text(encoding='utf-8') + (ROOT / 'widgets/sowhat-category.js').read_text(encoding='utf-8')
    return head + '<style>\n' + css + '\n</style>\n' + body + '\n<script>\n' + js + '\n</script>\n</body></html>\n'


def letter_url(item: dict) -> str:
    return f'{CANONICAL}letters/{item["volume"]}/'


def render_letter(item: dict, summary: dict, cache_entry: dict, newer: dict | None, older: dict | None) -> str:
    canonical = letter_url(item)
    title = f'Vol. {item["volume"]} {item["title"]} | 쏘왓레터'
    story_titles = ' · '.join(headline for _, headline, _ in summary['stories'][:3])
    description = sowhat_summaries.short_excerpt(summary['introduction'] or story_titles, 155)
    published = sowhat_summaries.published_at(item, cache_entry)
    datetime_value = published.isoformat() if published else item['date']
    display_date = published.strftime('%Y.%m.%d %H:%M KST') if published else item['date'].replace('-', '.')
    image = item.get('image', '')
    graph = [{
        '@type': 'Article', '@id': canonical + '#summary', 'url': canonical,
        'headline': item['title'], 'description': description, 'inLanguage': 'ko-KR',
        'datePublished': datetime_value, 'mainEntityOfPage': canonical,
        'publisher': {'@type': 'Organization', 'name': '중기이코노미'},
    }]
    if image:
        graph[0]['image'] = image
    head = page_head(title, description, canonical, title, description, graph, share_image=image, article=True)
    template = (ROOT / 'widgets/sowhat-archive-template.html').read_text(encoding='utf-8')
    template = sowhat_letter_page.fill_template(template, json.loads((ROOT / 'data/sowhat_archive.json').read_text(encoding='utf-8'))['items'])
    css = (ROOT / 'widgets/sowhat-archive.css').read_text(encoding='utf-8')
    letter_css = (ROOT / 'widgets/sowhat-letter.css').read_text(encoding='utf-8')
    js = (ROOT / 'widgets/sowhat-archive.js').read_text(encoding='utf-8')
    return sowhat_letter_page.render(item, cache_entry, summary['introduction'], newer, older, head, template, css, letter_css, js)


def sitemap(payload: dict, cache: dict | None = None, summaries: dict | None = None) -> str:
    root = Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    months = list(Counter(x['date'][:7] for x in payload['items']))
    for key in ['',*months]:
        items = [x for x in payload['items'] if not key or x['date'].startswith(key)]
        entry = SubElement(root,'url')
        SubElement(entry,'loc').text = month_url(key)
        SubElement(entry,'lastmod').text = max(x['date'] for x in items)
    if cache is not None:
        groups = sowhat_sections.by_category(payload['items'], cache)
        for label, slug, _ in sowhat_sections.CATEGORIES:
            if groups[label]:
                entry = SubElement(root,'url')
                SubElement(entry,'loc').text = category_url(slug)
                SubElement(entry,'lastmod').text = groups[label][0][0]['date']
    for item in payload['items']:
        if item['id'] in (summaries or {}):
            SubElement(SubElement(root, 'url'), 'loc').text = letter_url(item)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root,encoding='unicode') + '\n'


FIRST_SEEN = ROOT / 'data' / 'sowhat_first_seen.json'


def record_first_seen(items: list[dict], now: datetime | None = None) -> dict:
    """When each issue first appeared on this archive (= its RSS publish time).

    Issues already here before this was added are stored as null (time unknown, so no
    made-up time); every issue that shows up later gets the build time that added it.
    """
    kst = timezone(timedelta(hours=9))
    try:
        seen = json.loads(FIRST_SEEN.read_text(encoding='utf-8'))
    except FileNotFoundError:
        seen = None
    if seen is None:
        seen = {x['id']: None for x in items}
    stamp = (now or datetime.now(kst)).astimezone(kst).replace(microsecond=0).isoformat()
    changed = False
    for x in items:
        if x['id'] not in seen:
            seen[x['id']] = stamp
            changed = True
    if changed or not FIRST_SEEN.exists():
        FIRST_SEEN.write_text(json.dumps(seen, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return seen


def rss(payload: dict, cache: dict, summaries: dict, limit: int = 30, *, previous: str = '', first_seen: dict | None = None) -> str:
    """Publish the latest issues with stable GUIDs and the summary page's full editorial text."""
    issues = cache.get('issues', {})
    first_seen = first_seen or {}
    items = sorted(payload['items'], key=lambda x: x['date'], reverse=True)[:limit]
    root = Element('rss', version='2.0')
    ch = SubElement(root, 'channel')
    SubElement(ch, 'title').text = '쏘왓레터'
    SubElement(ch, 'link').text = CANONICAL
    SubElement(ch, 'description').text = SITE_DESCRIPTION
    SubElement(ch, 'language').text = 'ko'
    SubElement(ch, f'{{{ATOM_NS}}}link', href=CANONICAL+'rss.xml', rel='self', type='application/rss+xml')
    for x in items:
        it = SubElement(ch, 'item')
        vol = x.get('volume')
        SubElement(it, 'title').text = (f'Vol.{vol} ' if vol else '') + x['title']
        summary = summaries.get(x['id'])
        SubElement(it, 'link').text = letter_url(x) if summary else month_url(x['date'][:7]) + (f'#vol-{vol}' if vol else '')
        guid = SubElement(it, 'guid', isPermaLink='false'); guid.text = f'sowhat-{x["id"]}'
        entry = issues.get(x['id'], {})
        published = sowhat_summaries.published_at(x, entry)
        if not published and first_seen.get(x['id']):
            published = datetime.fromisoformat(first_seen[x['id']])
        if published:
            SubElement(it, 'pubDate').text = format_datetime(published)
        sections = entry.get('sections', [])
        for label in dict.fromkeys(s['cat'] for s in sections):
            SubElement(it, 'category').text = label
        SubElement(it, 'description').text = sowhat_summaries.body(summary) if summary else escape(x['title'])
    stamp = None
    try:
        old = fromstring(previous)
        old_channel = old.find('channel')
        old_stamp = old_channel.find('lastBuildDate') if old_channel is not None else None
        if old_stamp is not None:
            old_channel.remove(old_stamp)
            if tostring(old) == tostring(root):
                stamp = old_stamp.text
    except ParseError:
        pass
    last_build = Element('lastBuildDate')
    last_build.text = stamp or format_datetime(datetime.now(timezone.utc).replace(microsecond=0), usegmt=True)
    ch.insert(5, last_build)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding='unicode') + '\n'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh',action='store_true')
    args = parser.parse_args()
    if args.refresh:
        refresh()
    result = build()
    data = json.loads((ROOT / 'data/sowhat_archive.json').read_text(encoding='utf-8'))
    cache = sowhat_sections.update(data['items'], fetch=args.refresh)
    summaries = sowhat_summaries.collect(data['items'], cache)
    months = list(Counter(x['date'][:7] for x in data['items']))
    for key in ['',*months]:
        destination = ROOT / (key.replace('-','/') if key else '') / 'index.html'
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(sowhat_sections.with_analytics(render_page(data, key)), encoding='utf-8')
    letters = [item for item in data['items'] if item['id'] in summaries]
    # next/previous buttons walk the summaries from Vol. 16 (newest first); older pages keep only the way back
    nav = sowhat_letter_page.navigable(data['items'], summaries)
    position = {item['id']: i for i, item in enumerate(nav)}
    letter_dir = ROOT / 'letters'
    for item in letters:
        i = position.get(item['id'])
        newer = nav[i - 1] if i is not None and i > 0 else None
        older = nav[i + 1] if i is not None and i + 1 < len(nav) else None
        destination = letter_dir / str(item['volume']) / 'index.html'
        destination.parent.mkdir(parents=True, exist_ok=True)
        html = render_letter(item, summaries[item['id']], cache.get('issues', {}).get(item['id'], {}), newer, older)
        destination.write_text(sowhat_sections.with_analytics(html), encoding='utf-8')
    volumes = {str(item['volume']) for item in letters}
    for old in letter_dir.glob('*/index.html'):
        if old.parent.name.isdecimal() and old.parent.name not in volumes:
            old.unlink()
    for label, slug, _ in sowhat_sections.CATEGORIES:
        destination = ROOT / 'category' / slug / 'index.html'
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(sowhat_sections.with_analytics(render_category_page(data,cache,label)),encoding='utf-8')
    reader = ROOT / 'read' / 'index.html'
    reader.parent.mkdir(exist_ok=True)
    reader.write_text(sowhat_sections.with_analytics((ROOT / 'widgets/sowhat-reader.html').read_text(encoding='utf-8')),encoding='utf-8')
    (ROOT / 'CNAME').write_text('sowhat.bestexit.co.kr\n',encoding='utf-8')
    (ROOT / '.nojekyll').write_text('',encoding='utf-8')
    (ROOT / 'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /widgets/\nSitemap: '+CANONICAL+'sitemap.xml\n',encoding='utf-8')
    (ROOT / 'sitemap.xml').write_text(sitemap(data, cache, summaries), encoding='utf-8')
    feed = ROOT / 'rss.xml'
    previous = feed.read_text(encoding='utf-8') if feed.exists() else ''
    feed.write_text(rss(data, cache, summaries, previous=previous, first_seen=record_first_seen(data['items'])), encoding='utf-8')
    result['pages'] = 1 + len(months)
    result['categories'] = len(sowhat_sections.CATEGORIES)
    result['letters'] = len(letters)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
