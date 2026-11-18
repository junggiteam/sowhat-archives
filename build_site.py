"""Build a static, crawlable archive for sowhat.bestexit.co.kr.

The public upstream manifest is shared with the Imweb widget. Scheduled builds
refresh the initial HTML as well, so new cards do not depend on JavaScript for
discovery by search engines. No account tokens or subscriber data are required.
"""
from pathlib import Path
from html import escape
from collections import Counter
import argparse
import json
import time
import urllib.request
from xml.etree.ElementTree import Element, SubElement, tostring

from build_sowhat_widget import build, render_widget, month_name, month_url

ROOT = Path(__file__).resolve().parent
CANONICAL = 'https://sowhat.bestexit.co.kr/'
UPSTREAM = 'https://raw.githubusercontent.com/junggiteam/naver-news/main/data/sowhat_archive.json'
VERIFICATION = json.loads((ROOT / 'site-verification.json').read_text(encoding='utf-8'))


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


def page_title(archive_month: str) -> str:
    return ((month_name(archive_month) + ' ') if archive_month else '') + '쏘왓레터 모아보기 | 중기이코노미 · 베스트엑싯'


def render_page(payload: dict, archive_month: str = '') -> str:
    items = [x for x in payload['items'] if not archive_month or x['date'].startswith(archive_month)]
    canonical = month_url(archive_month)
    title = page_title(archive_month)
    description = (f'{month_name(archive_month)} 중기이코노미 쏘왓레터 {len(items)}개 발행호를 모아보세요. ' if archive_month else '중기이코노미 쏘왓레터의 경제·기업·M&A·기업승계·세무 인사이트를 만나보세요. ') + '대표이미지와 제목으로 지난 뉴스레터를 검색하고 원문 읽기와 구독 신청을 할 수 있습니다.'
    graph = [
        {'@type':'WebSite','@id':CANONICAL+'#website','url':CANONICAL,'name':'쏘왓레터 모아보기','alternateName':'SO WHAT?','inLanguage':'ko-KR','publisher':{'@type':'Organization','name':'중기이코노미'}},
    ]
    if archive_month:
        graph.append({'@type':'BreadcrumbList','itemListElement':[
            {'@type':'ListItem','position':1,'name':'쏘왓레터 모아보기','item':CANONICAL},
            {'@type':'ListItem','position':2,'name':month_name(archive_month),'item':canonical},
        ]})
    structured = json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('<','\\u003c')
    image = CANONICAL+'assets/sowhat-share.png'
    head = f'''<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description,quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="naver-site-verification" content="{escape(VERIFICATION['naver'],quote=True)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="preconnect" href="https://img2.stibee.com">
<link rel="dns-prefetch" href="https://raw.githubusercontent.com">
<meta property="og:type" content="website">
<meta property="og:locale" content="ko_KR">
<meta property="og:site_name" content="중기이코노미 쏘왓레터">
<meta property="og:title" content="{escape(title,quote=True)}">
<meta property="og:description" content="{escape(description,quote=True)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="중기이코노미 쏘왓레터 모아보기 — 경제·기업·M&A·기업승계·세무 뉴스레터">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(title,quote=True)}">
<meta name="twitter:description" content="{escape(description,quote=True)}">
<meta name="twitter:image" content="{image}">
<meta name="theme-color" content="#d12f30">
<script type="application/ld+json">{structured}</script>
<style>body{{margin:0;background:#fff}}</style>
</head><body>'''
    return head + render_widget(payload['items'],archive_month) + '</body></html>\n'


def sitemap(payload: dict) -> str:
    root = Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    months = list(Counter(x['date'][:7] for x in payload['items']))
    for key in ['',*months]:
        items = [x for x in payload['items'] if not key or x['date'].startswith(key)]
        entry = SubElement(root,'url')
        SubElement(entry,'loc').text = month_url(key)
        SubElement(entry,'lastmod').text = max(x['date'] for x in items)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root,encoding='unicode') + '\n'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh',action='store_true')
    args = parser.parse_args()
    if args.refresh:
        refresh()
    result = build()
    data = json.loads((ROOT / 'data/sowhat_archive.json').read_text(encoding='utf-8'))
    months = list(Counter(x['date'][:7] for x in data['items']))
    for key in ['',*months]:
        destination = ROOT / (key.replace('-','/') if key else '') / 'index.html'
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(render_page(data,key),encoding='utf-8')
    (ROOT / 'CNAME').write_text('sowhat.bestexit.co.kr\n',encoding='utf-8')
    (ROOT / '.nojekyll').write_text('',encoding='utf-8')
    (ROOT / 'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /widgets/\nSitemap: '+CANONICAL+'sitemap.xml\n',encoding='utf-8')
    (ROOT / 'sitemap.xml').write_text(sitemap(data),encoding='utf-8')
    result['pages'] = 1 + len(months)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
