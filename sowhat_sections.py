"""Category sections of each So What issue (기업·금융·투자·M&A·IPO·승계·TAX·재테크).

Each published issue on Stibee lists its sections twice: a short table of
contents ("M&A | headline") and then the section itself (label, full
headline, image, body). We read the second occurrence of each label and keep
the headline, the section's own image and a short excerpt. Results are cached
in data/sowhat_sections.json so every issue is fetched only once.
"""
from html import unescape
from pathlib import Path
import json
import re
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'data/sowhat_sections.json'
MIN_VOLUME = 16  # issues up to Vol. 15 used a different layout
LABELS = ['시황', '기업', '금융', '투자', 'M&A', 'IPO', '승계', 'TAX', '재테크']
CATEGORIES = [
    # (label, slug, intro)
    ('기업', 'company', '기업 현장의 이슈와 경영 판단에 필요한 정보를 모았습니다.'),
    ('금융', 'finance', '금리·대출·정책금융처럼 기업과 개인에 영향을 주는 금융 소식을 모았습니다.'),
    ('투자', 'invest', '증시 흐름과 투자 판단에 도움이 되는 시장 이야기를 모았습니다.'),
    ('M&A', 'ma', '기업 인수·매각 동향과 거래 구조, 몸값을 매기는 방법을 모았습니다.'),
    ('IPO', 'ipo', '상장을 준비하는 기업과 공모 시장의 흐름을 모았습니다.'),
    ('승계', 'succession', '가업승계와 지분 이전, 상속·증여 설계의 핵심을 모았습니다.'),
    ('TAX', 'tax', '기업과 대표가 알아야 할 세금 이슈와 절세 방법을 모았습니다.'),
    ('재테크', 'wealth', '자산을 지키고 불리는 데 필요한 재테크 정보를 모았습니다.'),
]
ISSUE_DIR = ROOT / 'issue'  # hosted copy of each issue: issue/<volume>/index.html
SITE = 'https://sowhat.bestexit.co.kr/'
IMAGE_HOSTS = ('https://img.stibee.com/', 'https://img2.stibee.com/', 'https://resource.stibee.com/')


def extract(document: str) -> list[dict]:
    """Return [{cat, headline, excerpt, image}] in page order."""
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', document, flags=re.S | re.I)
    body = re.sub(r'<br\s*/?>', '\n', body, flags=re.I)
    tokens = []
    for m in re.finditer(r'<img[^>]*?src="([^"]+)"[^>]*>|>([^<]+)<', body):
        if m.group(1):
            tokens.append(('img', unescape(m.group(1))))
        else:
            for line in unescape(m.group(2)).split('\n'):
                line = re.sub(r'\s+', ' ', line).strip()
                if line:
                    tokens.append(('text', line))
    seen, sections, current = {}, [], None
    for kind, value in tokens:
        if kind == 'text' and value in LABELS:
            seen[value] = seen.get(value, 0) + 1
            if seen[value] == 2:
                current = {'cat': value, 'headline': '', 'text': [], 'image': ''}
                sections.append(current)
            continue
        if current is None:
            continue
        if kind == 'img':
            if not current['image'] and value.startswith(IMAGE_HOSTS):
                current['image'] = value
        elif not current['headline']:
            current['headline'] = value
        elif len(value) > 15 and sum(len(x) for x in current['text']) < 400:
            current['text'].append(value)
    result = []
    for s in sections:
        if not s['headline'] or s['cat'] == '시황':
            continue
        excerpt = ' '.join(s['text'])
        if len(excerpt) > 220:
            excerpt = excerpt[:220].rsplit(' ', 1)[0] + '…'
        result.append({'cat': s['cat'], 'headline': s['headline'][:160], 'excerpt': excerpt, 'image': s['image']})
    return result


ISSUE_START, ISSUE_END = '<!--swa-issue-->', '<!--/swa-issue-->'


def issue_path(volume: int) -> Path:
    return ISSUE_DIR / str(volume) / 'index.html'


def issue_url(volume: int, slug: str) -> str:
    """Hosted copy that opens with that category's section heading at the top."""
    return f'{SITE}issue/{volume}/#c={slug}'


def write_issue_page(item: dict, document: str) -> None:
    """Save the public Stibee web version with a small jump script and a back bar.

    The Stibee page lists every section twice (contents, then the section), and a
    browser text fragment can only centre the first match, so we host a copy and
    scroll to the second occurrence of the label ourselves.
    """
    document = re.sub(re.escape(ISSUE_START) + '.*?' + re.escape(ISSUE_END), '', document, flags=re.S)
    labels = {slug: label for label, slug, _ in CATEGORIES}
    head = (f'{ISSUE_START}<meta name="robots" content="noindex,follow">'
            f'<link rel="canonical" href="{item["url"]}">{ISSUE_END}')
    tail = (ISSUE_START +
            '<style>.swa-issue-bar{position:fixed;left:0;right:0;bottom:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;gap:8px;'
            'min-height:56px;box-sizing:border-box;padding:12px 20px calc(12px + env(safe-area-inset-bottom));background:#d12f30;color:#fff!important;'
            "font:800 17px/1.4 Pretendard,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif;letter-spacing:-.03em;"
            'text-decoration:none!important;box-shadow:0 -4px 16px rgba(25,32,48,.12)}'
            '.swa-issue-bar svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}'
            # like the volume reader: the newsletter's own bottom padding runs under the bar
            '@media(max-width:820px){body{padding-bottom:0!important}.stb-container-full{padding-bottom:64px!important}}'
            # PC: no bar (mobile only, like the volume reader)
            '@media(min-width:821px){.swa-issue-bar{display:none!important}}</style>'
            f'<a class="swa-issue-bar" href="{SITE}" data-swa-back><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg><span>쏘왓레터 모아보기로 가기</span></a>'
            '<script>(function(){var L=' + json.dumps(labels, ensure_ascii=False) + ',S="' + SITE + '";'
            'var m=/(?:^|&)c=([a-z]+)/.exec(location.hash.slice(1));var label=m&&L[m[1]];if(!label)return;'
            'var back=document.querySelector("[data-swa-back]");if(back){back.href=S+"category/"+m[1]+"/?r=1";back.lastChild.textContent=label+" 모아보기로 가기";}'
            'function find(){var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null),n,c=0;'
            'while((n=w.nextNode())){if(n.nodeValue.replace(/\\s+/g," ").trim()===label&&++c===2)return n.parentElement;}return null}'
            'var done=false;function go(){if(done)return;var el=find();if(!el)return;'
            'window.scrollTo(0,Math.max(0,el.getBoundingClientRect().top+(window.pageYOffset||0)-16));}'
            'function stop(){done=true}["wheel","touchstart","keydown","mousedown"].forEach(function(e){window.addEventListener(e,stop,{passive:true})});'
            'if("scrollRestoration" in history)history.scrollRestoration="manual";'
            'go();Array.prototype.forEach.call(document.images,function(i){if(!i.complete)i.addEventListener("load",go)});'
            'window.addEventListener("load",function(){go();setTimeout(go,300);setTimeout(stop,1500)});setTimeout(stop,8000);})();</script>'
            + ISSUE_END)
    # Root-relative assets (Stibee's page stylesheet) must keep loading from stibee.com.
    document = re.sub(r'(\s(?:src|href)=")/(?!/)', r'\1https://stibee.com/', document)
    document = document.replace('</head>', head + '</head>', 1)
    # The Stibee page nests the e-mail document (with its own </body>) inside the page
    # and its script keeps only the e-mail container, so append to the outer body.
    cut = document.rfind('</body>')
    document = document[:cut] + tail + document[cut:] if cut >= 0 else document + tail
    path = issue_path(item['volume'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding='utf-8')


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding='utf-8'))
    return {'schemaVersion': 1, 'issues': {}}


def update(items: list[dict], fetch: bool) -> dict:
    """Fill the cache for eligible issues; network only when fetch=True."""
    cache = load_cache()
    issues = cache.setdefault('issues', {})
    changed = False
    for item in items:
        if not fetch or not item.get('volume') or item['volume'] < MIN_VOLUME:
            continue
        if item['id'] in issues and issue_path(item['volume']).exists():
            continue
        try:
            req = urllib.request.Request(item['url'], headers={'User-Agent': 'Mozilla/5.0 (SoWhatArchive)'})
            with urllib.request.urlopen(req, timeout=30) as response:
                document = response.read().decode('utf-8', 'replace')
        except Exception:
            continue
        sections = extract(document)
        if not sections:
            continue
        write_issue_page(item, document)
        if item['id'] not in issues:
            issues[item['id']] = {'volume': item['volume'], 'date': item['date'], 'url': item['url'], 'sections': sections}
            changed = True
        time.sleep(0.3)
    if changed:
        CACHE.parent.mkdir(exist_ok=True)
        tmp = CACHE.with_suffix('.tmp')
        tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        tmp.replace(CACHE)
    return cache


def by_category(items: list[dict], cache: dict) -> dict:
    """{label: [(item, section), ...]} newest first, only published issues."""
    out = {label: [] for label, _, _ in CATEGORIES}
    issues = cache.get('issues', {})
    for item in sorted(items, key=lambda x: x['date'], reverse=True):
        entry = issues.get(item['id'])
        if not entry or (item.get('volume') or 0) < MIN_VOLUME:
            continue
        for section in entry['sections']:
            if section['cat'] in out:
                out[section['cat']].append((item, section))
    return out
