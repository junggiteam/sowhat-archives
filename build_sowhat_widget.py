"""Generate the full Imweb widget; cards are also present before JavaScript."""
from collections import Counter
from html import escape
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
WIDGETS = ROOT / 'widgets'


BASE = 'https://sowhat.bestexit.co.kr/'


def month_name(key: str) -> str:
    return f'{key[:4]}년 {int(key[5:])}월'


def month_url(key: str) -> str:
    return BASE + key.replace('-', '/') + '/' if key else BASE


def render_widget(all_items: list[dict], archive_month: str = '') -> str:
    data = [x for x in all_items if not archive_month or x['date'].startswith(archive_month)]
    canonical = month_url(archive_month)
    cards = []
    for i, item in enumerate(data):
        title = escape(item['title'])
        image = f'<img src="{escape(item["image"], quote=True)}" alt="{title}" width="630" height="360" loading="{"eager" if i < 3 else "lazy"}" decoding="async">' if item.get('image') else '<span class="swa-cover-fallback">SO WHAT?</span>'
        volume = 'Vol. ' + str(item['volume']).zfill(3) if item.get('volume') else 'SO WHAT LETTER'
        cards.append(f'<article class="swa-card"><a href="{escape(item["url"], quote=True)}" target="_blank" rel="noopener" aria-label="{title} — 스티비 원문 새 창"><div class="swa-cover">{image}</div><div class="swa-card-body"><p class="swa-meta"><span class="swa-volume">{volume}</span><time datetime="{item["date"]}"><svg class="swa-cal" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>{item["date"].replace("-", ".")}</time></p><h2 title="{title}">{title}</h2></div></a></article>')
    counts = Counter(x['date'][:7] for x in all_items)
    current = ' aria-current="page"' if not archive_month else ''
    month_links = f'<a class="swa-month-link" href="{BASE}"{current}>전체 뉴스레터 <span>{len(all_items)}</span></a>'
    for key, value in counts.items():
        current = ' aria-current="page"' if key == archive_month else ''
        month_links += f'<a class="swa-month-link" href="{month_url(key)}"{current}>{month_name(key)} <span>{value}</span></a>'
    name = (month_name(archive_month) + ' ' if archive_month else '') + '쏘왓레터 모아보기'
    heading = '<span class="swa-title-letter">쏘왓레터</span><span class="swa-title-archive">모아보기</span>'
    intro = (
        '경제 뉴스를 읽고도 “그래서 어쩌라고?(So What)” 싶으셨나요?',
        '쏘왓레터는 복잡한 정보는 덜어내고, 바로 쓸 수 있는 ‘결론’만 전합니다.',
        '막연한 정보 대신 선명한 판단 기준, 지금 쏘왓레터로 받아보세요.',
    )
    description = ''.join(f'<p>{escape(line)}</p>' for line in intro)
    structured = {'@context':'https://schema.org','@type':'CollectionPage','@id':canonical+'#archive','name':name,'url':canonical,'inLanguage':'ko-KR','isPartOf':{'@id':BASE+'#website'},'mainEntity':{'@type':'ItemList','numberOfItems':len(data),'itemListElement':[{'@type':'ListItem','position':i+1,'item':{'@type':'CreativeWork','name':x['title'],'url':x['url'],'datePublished':x['date'],**({'image':x['image']} if x.get('image') else {})}} for i,x in enumerate(data)]}}
    template = (WIDGETS / 'sowhat-archive-template.html').read_text(encoding='utf-8')
    label = month_name(archive_month) + ' 뉴스레터' if archive_month else '모든 뉴스레터'
    markup = template.replace('__CANONICAL__',canonical).replace('__ARCHIVE_MONTH__',archive_month).replace('__HEADING__',heading).replace('__DESCRIPTION__',description).replace('__GRID_LABEL__',label).replace('__COUNT__', str(len(data))).replace('__CARDS__','\n'.join(cards)).replace('__MONTH_LINKS__', month_links).replace('__DATA__', json.dumps(all_items,ensure_ascii=False).replace('<','\\u003c')).replace('__STRUCTURED__',json.dumps(structured,ensure_ascii=False).replace('<','\\u003c'))
    css = (WIDGETS / 'sowhat-archive.css').read_text(encoding='utf-8')
    js = (WIDGETS / 'sowhat-archive.js').read_text(encoding='utf-8')
    result = '<style>\n' + css + '\n</style>\n' + markup + '\n<script>\n' + js + '\n</script>\n'
    return result


def build() -> dict:
    data = json.loads((ROOT / 'data/sowhat_archive.json').read_text(encoding='utf-8'))['items']
    result = render_widget(data).replace('src="/assets/','src="'+BASE+'assets/')
    (WIDGETS / 'sowhat-archives-code.txt').write_text(result,encoding='utf-8')
    preview = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>쏘왓레터 모아보기 · 베스트엑싯</title><style>body{margin:0;background:#fff}</style></head><body>' + result + '</body></html>'
    (WIDGETS / 'sowhat-archives-preview.html').write_text(preview,encoding='utf-8')
    return {'items':len(data),'characters':len(result)}


if __name__ == '__main__':
    print(json.dumps(build()))
