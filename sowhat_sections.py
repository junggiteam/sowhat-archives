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
    ('기업', 'company', '기업 현장의 이슈와 경영 판단에 필요한 포인트를 모았습니다.'),
    ('금융', 'finance', '금리·대출·정책금융처럼 기업과 개인에 영향을 주는 금융 소식을 모았습니다.'),
    ('투자', 'invest', '증시 흐름과 투자 판단에 도움이 되는 시장 이야기를 모았습니다.'),
    ('M&A', 'ma', '기업 인수·매각 동향과 거래 구조, 몸값 산정 포인트를 모았습니다.'),
    ('IPO', 'ipo', '상장을 준비하는 기업과 공모 시장의 흐름을 모았습니다.'),
    ('승계', 'succession', '가업승계와 지분 이전, 상속·증여 설계의 핵심을 모았습니다.'),
    ('TAX', 'tax', '기업과 대표가 알아야 할 세금 이슈와 절세 포인트를 모았습니다.'),
    ('재테크', 'wealth', '자산을 지키고 불리는 데 필요한 재테크 정보를 모았습니다.'),
]
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
        if not item.get('volume') or item['volume'] < MIN_VOLUME or item['id'] in issues or not fetch:
            continue
        try:
            req = urllib.request.Request(item['url'], headers={'User-Agent': 'Mozilla/5.0 (SoWhatArchive)'})
            with urllib.request.urlopen(req, timeout=30) as response:
                sections = extract(response.read().decode('utf-8', 'replace'))
        except Exception:
            continue
        if not sections:
            continue
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
