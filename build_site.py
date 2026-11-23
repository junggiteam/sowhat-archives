"""Build a static, crawlable archive for sowhat.bestexit.co.kr.

The public upstream manifest is shared with the Imweb widget. Scheduled builds
refresh the initial HTML as well, so new cards do not depend on JavaScript for
discovery by search engines. No account tokens or subscriber data are required.
"""
from pathlib import Path
from html import escape
from collections import Counter
from datetime import datetime, timezone
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
    return '중기이코노미 쏘왓레터 모아보기 | 경제·경영 뉴스레터'


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


def render_page(payload: dict, archive_month: str = '', summaries: dict | None = None) -> str:
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
    latest_summary = next((item for item in items if item['id'] in (summaries or {})), None)
    return head + render_widget(payload['items'], archive_month, letter_url(latest_summary) if latest_summary else '') + '</body></html>\n'


def category_url(slug: str) -> str:
    return CANONICAL + 'category/' + slug + '/'


def render_category_page(payload: dict, cache: dict, label: str) -> str:
    """One category (e.g. M&A): each issue's section for it, newest first."""
    slug, intro = next((s2, i) for l, s2, i in sowhat_sections.CATEGORIES if l == label)
    rows = sowhat_sections.by_category(payload['items'], cache)[label]
    canonical = category_url(slug)
    topic_title = {
        'company': '기업 경영 뉴스레터 모아보기',
        'ma': 'M&A 정보와 인수합병 동향 모아보기',
        'succession': '기업승계 뉴스레터 모아보기',
        'tax': '기업 세무·절세 뉴스레터 모아보기',
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
    template = (ROOT / 'widgets/sowhat-archive-template.html').read_text(encoding='utf-8')
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


def render_letter(item: dict, summary: dict, cache_entry: dict, adjacent: list[tuple[str, dict]]) -> str:
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
    head = head.replace('</head>', '<link rel="stylesheet" href="/assets/sowhat-summary.css">\n</head>', 1)
    cover = f'\n    <img src="{escape(image, quote=True)}" alt="" width="630" height="360">' if image else ''
    category_names = {category for category, _, _ in summary['stories']}
    related = ''.join(f'<a href="{category_url(slug)}">{escape(label)} 뉴스레터</a>'
                      for label, slug, _ in sowhat_sections.CATEGORIES if label in category_names)
    other_issues = ''.join(f'<a href="{letter_url(other)}">{label} Vol. {other["volume"]}</a>' for label, other in adjacent)
    categories = f'\n    <nav aria-label="관련 카테고리">{related}</nav>' if related else ''
    month = month_url(item['date'][:7])
    return head + f'''
<main class="letter">
  <nav aria-label="아카이브"><a href="{CANONICAL}">쏘왓레터 모아보기</a><a href="{month}">{month_name(item['date'][:7])}</a></nav>
  <article>
    <p class="issue-date">Vol. {item['volume']} · <time datetime="{datetime_value}">{display_date}</time></p>
    <h1>{escape(item['title'])}</h1>{cover}
    <section aria-labelledby="issue-summary"><h2 id="issue-summary">이번 호 요약</h2>{sowhat_summaries.body(summary)}</section>
  </article>
  <div class="letter-actions">
    <nav aria-label="발행호"><a href="{escape(item['url'], quote=True)}">뉴스레터 읽기</a>{other_issues}</nav>{categories}
  </div>
</main></body></html>
'''


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


def rss(payload: dict, cache: dict, summaries: dict, limit: int = 30, *, previous: str = '') -> str:
    """Publish the latest issues with stable GUIDs and the summary page's full editorial text."""
    issues = cache.get('issues', {})
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
        destination.write_text(sowhat_sections.with_analytics(render_page(data, key, summaries)), encoding='utf-8')
    letters = [item for item in data['items'] if item['id'] in summaries]
    letter_dir = ROOT / 'letters'
    for index, item in enumerate(letters):
        adjacent = []
        if index + 1 < len(letters):
            adjacent.append(('이전 호', letters[index + 1]))
        if index > 0:
            adjacent.append(('다음 호', letters[index - 1]))
        destination = letter_dir / str(item['volume']) / 'index.html'
        destination.parent.mkdir(parents=True, exist_ok=True)
        html = render_letter(item, summaries[item['id']], cache.get('issues', {}).get(item['id'], {}), adjacent)
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
    feed.write_text(rss(data, cache, summaries, previous=previous), encoding='utf-8')
    result['pages'] = 1 + len(months)
    result['categories'] = len(sowhat_sections.CATEGORIES)
    result['letters'] = len(letters)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
