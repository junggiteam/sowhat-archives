"""Category sections of each So What issue (기업·금융·투자·M&A·IPO·승계·TAX·재테크).

Each published issue on Stibee lists its sections twice: a short table of
contents ("M&A | headline") and then the section itself (label, full
headline, image, body). We read the second occurrence of each label and keep
the headline, the section's own image and a short excerpt. Results are cached
in data/sowhat_sections.json so every issue is fetched only once.
"""
from html import unescape
from html.parser import HTMLParser
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
    ('기업', 'company', '기업의 실적, 사업 전략과 주요 경영 이슈를 정리한 기업 뉴스레터입니다.'),
    ('금융', 'finance', '금리·대출·정책금융처럼 기업과 개인에 영향을 주는 소식을 모은 금융 뉴스레터입니다.'),
    ('투자', 'invest', '증시 흐름과 투자 판단에 도움이 되는 시장 이야기를 모은 투자 뉴스레터입니다.'),
    ('M&A', 'ma', '기업 인수합병·매각 동향과 거래 구조, 기업가치를 다룬 M&A 뉴스레터입니다.'),
    ('IPO', 'ipo', '상장을 준비하는 기업과 공모 시장의 흐름을 모은 IPO 뉴스레터입니다.'),
    ('승계', 'succession', '가업승계와 지분 이전, 상속·증여 설계의 핵심을 모은 기업승계 뉴스레터입니다.'),
    ('TAX', 'tax', '기업과 대표가 알아야 할 세금 이슈와 절세 방법을 모은 세무 뉴스레터입니다.'),
    ('재테크', 'wealth', '자산관리와 절세 등 생활 속 재테크 정보를 모은 재테크 뉴스레터입니다.'),
]
ISSUE_DIR = ROOT / 'issue'  # hosted copy of each issue: issue/<volume>/index.html
SITE = 'https://sowhat.bestexit.co.kr/'
IMAGE_HOSTS = ('https://img.stibee.com/', 'https://img2.stibee.com/', 'https://resource.stibee.com/')


HEAD_MARK = '\u2063H\u2063'  # marks a story headline (Stibee's 22px semibold title) while tokenising
HEAD_RE = re.compile(r'<div style="[^"]*font-weight: ?600;[^"]*font-size: ?22px;[^"]*">(.*?)</div>', re.S)


def extract(document: str) -> list[dict]:
    """Return [{cat, n, headline, excerpt, image}] in page order.

    One category label can hold several stories (e.g. two M&A stories); each story
    headline (22px semibold) starts its own entry, numbered n = 1, 2, ... within the
    label. Older layouts without that headline style fall back to "first line after
    the label is the headline".
    """
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', document, flags=re.S | re.I)
    body = HEAD_RE.sub(lambda m: '<div>' + HEAD_MARK + re.sub(r'<[^>]+>', ' ', m.group(1)) + '</div>', body)
    body = re.sub(r'<br\s*/?>', '\n', body, flags=re.I)
    tokens = []
    for m in re.finditer(r'<img[^>]*?src="([^"]+)"[^>]*>|>([^<]+)<', body):
        if m.group(1):
            tokens.append(('img', unescape(m.group(1))))
            continue
        raw = unescape(m.group(2))
        if raw.lstrip().startswith(HEAD_MARK):
            text = re.sub(r'\s+', ' ', raw.replace(HEAD_MARK, ' ')).strip()
            if text:
                tokens.append(('head', text))
            continue
        for line in raw.split('\n'):
            line = re.sub(r'\s+', ' ', line).strip()
            if line:
                tokens.append(('text', line))
    seen, stories, cat, cur, count = {}, [], None, None, {}
    # Some issues put the picture above the headline, others below it. An image seen before
    # the section's first headline means "picture first": then each image waits for the next story.
    pending, picture_first = '', False
    for kind, value in tokens:
        if kind == 'text' and value in LABELS:
            seen[value] = seen.get(value, 0) + 1
            if seen[value] == 2:
                cat, cur, pending, picture_first = value, None, '', False
            continue
        if cat is None:
            continue
        if kind == 'head':
            if value.upper().replace(' ', '').startswith('SOWHAT'):
                continue  # the "SO WHAT" box title inside a story, not a new story
            count[cat] = count.get(cat, 0) + 1
            cur = {'cat': cat, 'n': count[cat], 'headline': value, 'text': [], 'image': pending}
            pending = ''
            stories.append(cur)
        elif kind == 'img':
            if not value.startswith(IMAGE_HOSTS):
                continue
            if cur is None:
                pending, picture_first = value, True
            elif picture_first:
                pending = value  # the picture right above the next headline
            elif not cur['image']:
                cur['image'] = value
        elif cur is None:
            count[cat] = count.get(cat, 0) + 1
            cur = {'cat': cat, 'n': count[cat], 'headline': value, 'text': [], 'image': pending}
            pending = ''
            stories.append(cur)
        elif len(value) > 15 and sum(len(x) for x in cur['text']) < 400:
            cur['text'].append(value)
    result = []
    for s in stories:
        if not s['headline'] or s['cat'] == '시황':
            continue
        excerpt = ' '.join(s['text'])
        if len(excerpt) > 220:
            excerpt = excerpt[:220].rsplit(' ', 1)[0] + '…'
        result.append({'cat': s['cat'], 'n': s['n'], 'headline': s['headline'][:160], 'excerpt': excerpt, 'image': s['image']})
    return result


def source_of_issue_page(volume: int) -> str:
    """The original Stibee HTML kept inside our hosted copy (our additions removed)."""
    return re.sub(re.escape(ISSUE_START) + '.*?' + re.escape(ISSUE_END), '', issue_path(volume).read_text(encoding='utf-8'), flags=re.S)


ISSUE_START, ISSUE_END = '<!--swa-issue-->', '<!--/swa-issue-->'
# Naver Analytics for sowhat.bestexit.co.kr (separate site from bestexit.co.kr), on every generated page.
NAVER_ANALYTICS = ('<script type="text/javascript" src="https://wcs.pstatic.net/wcslog.js"></script>'
                   '<script type="text/javascript">if(!wcs_add) var wcs_add = {};wcs_add["wa"] = "1fb672d3a8b6f00";if(window.wcs) { wcs_do(); }</script>')


def with_analytics(html: str) -> str:
    """Insert the Naver Analytics tag right before the last </body> (once)."""
    if 'wcs_add["wa"]' in html:
        return html
    cut = html.rfind('</body>')
    return html[:cut] + NAVER_ANALYTICS + html[cut:] if cut >= 0 else html + NAVER_ANALYTICS


def issue_path(volume: int) -> Path:
    return ISSUE_DIR / str(volume) / 'index.html'


def issue_url(volume: int, slug: str, n: int = 1) -> str:
    """Hosted copy that opens with that category's section heading (or its n-th story) at the top."""
    return f'{SITE}issue/{volume}/#c={slug}' + (f'&n={n}' if n and n > 1 else '')


def write_issue_page(item: dict, document: str) -> None:
    """Save the public Stibee web version with a small jump script and a back bar.

    The Stibee page lists every section twice (contents, then the section), and a
    browser text fragment can only centre the first match, so we host a copy and
    scroll to the second occurrence of the label ourselves.
    """
    document = re.sub(re.escape(ISSUE_START) + '.*?' + re.escape(ISSUE_END), '', document, flags=re.S)
    labels = {slug: label for label, slug, _ in CATEGORIES}
    head = (f'{ISSUE_START}<meta name="robots" content="noindex,follow">'
            f'<link rel="canonical" href="{item["url"]}"><link rel="icon" href="/favicon.ico?v=2" sizes="48x48"><link rel="icon" type="image/svg+xml" href="/assets/favicon.svg?v=2">{ISSUE_END}')
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
            'var h=location.hash.slice(1),m=/(?:^|&)c=([a-z]+)/.exec(h),nm=/(?:^|&)n=(\\d+)/.exec(h),N=nm?+nm[1]:1;var label=m&&L[m[1]];if(!label)return;'
            'var back=document.querySelector("[data-swa-back]");if(back){back.href=S+"category/"+m[1]+"/?r=1";back.lastChild.textContent=label+" 모아보기로 가기";}'
            'function find(){var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null),n,c=0;'
            'var lab=null;while((n=w.nextNode())){if(n.nodeValue.replace(/\\s+/g," ").trim()===label&&++c===2){lab=n.parentElement;break}}'
            # story 2, 3...: the N-th story headline (22px semibold, not the "SO WHAT" box) after the label
            'if(!lab||N<2)return lab;var hs=document.querySelectorAll(\'div[style*="font-size: 22px"],div[style*="font-size:22px"]\'),k=0;'
            'for(var i=0;i<hs.length;i++){var e=hs[i];if(!(lab.compareDocumentPosition(e)&4))continue;'
            'if(!/font-weight: ?600/.test(e.getAttribute("style")||""))continue;'
            'if(/^so ?what/i.test(e.textContent.trim()))continue;if(++k===N)return e;}return lab}'
            'var done=false;function go(){if(done)return;var el=find();if(!el)return;'
            'window.scrollTo(0,Math.max(0,el.getBoundingClientRect().top+(window.pageYOffset||0)-16));}'
            'function stop(){done=true}["wheel","touchstart","keydown","mousedown"].forEach(function(e){window.addEventListener(e,stop,{passive:true})});'
            'if("scrollRestoration" in history)history.scrollRestoration="manual";'
            'go();Array.prototype.forEach.call(document.images,function(i){if(!i.complete)i.addEventListener("load",go)});'
            'window.addEventListener("load",function(){go();setTimeout(go,300);setTimeout(stop,1500)});setTimeout(stop,8000);})();</script>'
            + NAVER_ANALYTICS + ISSUE_END)
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


class PublishedTime(HTMLParser):
    """Read explicitly labelled publication metadata from the share page head."""

    def __init__(self):
        super().__init__()
        self.value = None

    def handle_starttag(self, tag, attrs):
        if tag != 'meta' or self.value is not None:
            return
        fields = dict(attrs)
        if fields.get('property') == 'article:published_time' or fields.get('itemprop') == 'datePublished':
            self.value = fields.get('content')


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
            metadata = PublishedTime()
            metadata.feed(document.split('</head>', 1)[0])
            if metadata.value:
                issues[item['id']]['publishedAt'] = metadata.value
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
