"""Build a static, crawlable archive for sowhat.bestexit.co.kr.

The public upstream manifest is shared with the Imweb widget. Scheduled builds
refresh the initial HTML as well, so new cards do not depend on JavaScript for
discovery by search engines. No account tokens or subscriber data are required.
"""
from pathlib import Path
from html import escape
import argparse
import json
import sys
import time
import urllib.request

from build_sowhat_widget import build

ROOT = Path(__file__).resolve().parent
CANONICAL = 'https://sowhat.bestexit.co.kr/'
UPSTREAM = 'https://raw.githubusercontent.com/junggiteam/naver-news/main/data/sowhat_archive.json'


def refresh() -> None:
    request = urllib.request.Request(UPSTREAM, headers={'User-Agent':'BestExit-SoWhatSite/1.0'})
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh',action='store_true')
    args = parser.parse_args()
    if args.refresh:
        refresh()
    result = build()
    data = json.loads((ROOT / 'data/sowhat_archive.json').read_text(encoding='utf-8'))
    widget = (ROOT / 'widgets/sowhat-archives-code.txt').read_text(encoding='utf-8').replace('https://bestexit.co.kr/sowhat-archives',CANONICAL)
    image = escape(data['items'][0].get('image',''),quote=True)
    title = '쏘왓레터 모아보기 | 중기이코노미 · 베스트엑싯'
    description = '중기이코노미 쏘왓레터의 지난 발행호를 대표이미지와 제목으로 만나보세요. 경제·기업·M&A·기업승계·세무 인사이트를 검색하고 발행월별로 살펴볼 수 있습니다.'
    head = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><meta name="description" content="{description}"><meta name="robots" content="index,follow"><link rel="canonical" href="{CANONICAL}"><meta property="og:type" content="website"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:url" content="{CANONICAL}"><meta property="og:image" content="{image}"><meta name="twitter:card" content="summary_large_image"><style>body{{margin:0;background:#fff}}</style></head><body>'''
    (ROOT / 'index.html').write_text(head+widget+'</body></html>\n',encoding='utf-8')
    (ROOT / 'CNAME').write_text('sowhat.bestexit.co.kr\n',encoding='utf-8')
    (ROOT / '.nojekyll').write_text('',encoding='utf-8')
    (ROOT / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+CANONICAL+'sitemap.xml\n',encoding='utf-8')
    (ROOT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+CANONICAL+'</loc><lastmod>'+data['items'][0]['date']+'</lastmod></url></urlset>\n',encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
