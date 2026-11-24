"""Tell Naver (and Bing etc. via indexnow.org) which pages changed, so they crawl them soon.

IndexNow: the key file <KEY>.txt at the site root proves we own the site; the key is public
by design (it is not a secret).

  python ping_indexnow.py --all              every URL in sitemap.xml
  python ping_indexnow.py --changed HEAD~1   only pages whose HTML changed since that commit
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = 'https://sowhat.bestexit.co.kr/'
HOST = 'sowhat.bestexit.co.kr'
KEY = '74e6a769de984ce88cf24015f0755f0a'
ENDPOINTS = ('https://searchadvisor.naver.com/indexnow', 'https://api.indexnow.org/indexnow')


def sitemap_urls() -> list[str]:
    return re.findall(r'<loc>([^<]+)</loc>', (ROOT / 'sitemap.xml').read_text(encoding='utf-8'))


def changed_urls(since: str) -> list[str]:
    out = subprocess.run(['git', 'diff', '--name-only', since, 'HEAD', '--', '*.html'],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    known = set(sitemap_urls())
    urls = []
    for name in out:
        if not name.endswith('index.html'):
            continue
        url = SITE + name[:-len('index.html')]
        if url in known:
            urls.append(url)
    if urls and SITE not in urls:
        urls.insert(0, SITE)
    return urls


def ping(urls: list[str]) -> int:
    body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': f'{SITE}{KEY}.txt',
                       'urlList': urls[:10000]}).encode()
    failed = 0
    for endpoint in ENDPOINTS:
        req = urllib.request.Request(endpoint, data=body, method='POST',
                                     headers={'Content-Type': 'application/json; charset=utf-8'})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                print(endpoint, res.status, len(urls), 'urls')
        except urllib.error.HTTPError as e:
            print(endpoint, e.code, e.read()[:300].decode('utf-8', 'replace'))
            failed += e.code >= 400 and e.code != 429
        except Exception as e:  # network trouble must not fail the site build
            print(endpoint, 'error', e)
    return failed


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--all':
        targets = sitemap_urls()
    elif len(sys.argv) >= 3 and sys.argv[1] == '--changed':
        targets = changed_urls(sys.argv[2])
    else:
        sys.exit(__doc__)
    if not targets:
        print('nothing to send')
        sys.exit(0)
    sys.exit(1 if ping(targets) and '--strict' in sys.argv else 0)
