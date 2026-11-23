import json
import unittest
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from xml.etree import ElementTree

from build_site import CANONICAL, letter_url, render_letter, render_page, rss, sitemap
from sowhat_sections import PublishedTime
from sowhat_summaries import body, collect, published_at


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.canonicals, self.cards, self.structured = [], [], []
        self.h1 = 0
        self.in_card = False
        self.json_text = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs['href'])
        if tag == 'h1':
            self.h1 += 1
        if tag == 'article' and attrs.get('class') == 'swa-card':
            self.in_card = True
        if tag == 'a' and self.in_card:
            self.cards.append(attrs['href'])
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.json_text = ''

    def handle_data(self, text):
        if self.json_text is not None:
            self.json_text += text

    def handle_endtag(self, tag):
        if tag == 'article':
            self.in_card = False
        if tag == 'script' and self.json_text is not None:
            self.structured.append(json.loads(self.json_text))
            self.json_text = None


def fixture():
    return {'items':[
        {'id':'new','url':'https://stib.ee/new','date':'2026-11-18','title':'새 발행호','volume':115,'image':''},
        {'id':'next','url':'https://stib.ee/next','date':'2026-11-17','title':'이번 달 발행호','volume':114,'image':''},
        {'id':'old','url':'https://stib.ee/old','date':'2026-10-30','title':'지난 달 발행호','volume':101,'image':''},
    ]}


class SeoTests(unittest.TestCase):
    def test_root_delivers_every_card_and_single_canonical_without_javascript(self):
        page = Page(render_page(fixture()))
        self.assertEqual(page.canonicals,[CANONICAL])
        self.assertEqual(page.h1,1)
        self.assertEqual(len(page.cards),3)

    def test_month_keeps_only_its_own_cards_and_structured_items(self):
        page = Page(render_page(fixture(),'2026-11'))
        self.assertEqual(page.canonicals,[CANONICAL+'2026/11/'])
        self.assertEqual(page.cards,['https://stib.ee/new','https://stib.ee/next'])
        collection = next(x for x in page.structured if x.get('@type') == 'CollectionPage')
        self.assertEqual(collection['mainEntity']['numberOfItems'],2)
        self.assertEqual(collection['url'],page.canonicals[0])
        self.assertTrue(any(x.get('@type') == 'BreadcrumbList' for x in page.structured[0]['@graph']))

    def test_sitemap_contains_canonical_pages_and_real_publication_dates(self):
        tree = ElementTree.fromstring(sitemap(fixture()))
        ns = {'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        pages = {x.find('s:loc',ns).text:x.find('s:lastmod',ns).text for x in tree}
        self.assertEqual(pages,{CANONICAL:'2026-11-18',CANONICAL+'2026/11/':'2026-11-18',CANONICAL+'2026/10/':'2026-10-30'})

    def test_new_month_and_year_are_discoverable_automatically(self):
        data = fixture()
        data['items'].insert(0,{'id':'future','url':'https://stib.ee/future','date':'2027-01-02','title':'새해 발행호','volume':150,'image':''})
        root = render_page(data)
        self.assertIn('href="'+CANONICAL+'2027/01/"',root)
        self.assertIn(CANONICAL+'2027/01/',sitemap(data))
        self.assertEqual(Page(render_page(data,'2027-01')).cards,['https://stib.ee/future'])

    def test_titles_cannot_break_metadata_or_json_scripts(self):
        data = fixture()
        data['items'][0]['title'] = '<script>alert("headline")</script>'
        page = Page(render_page(data))
        self.assertEqual(len(page.structured),2)
        self.assertEqual(len(page.cards),3)

    def test_letters_and_feed_share_editorial_body_url_and_guid(self):
        data = fixture()
        cache = {'issues': {'new': {'sections': [{'cat': 'M&A', 'headline': '기업 매각 & 인수', 'excerpt': '첫 문장입니다. 다음 문장.'}]}}}
        summaries = collect(data['items'], cache)
        url = CANONICAL + 'letters/115/'
        newest = data['items'][0]
        self.assertEqual(letter_url(newest), url)
        html = render_letter(newest, summaries['new'], cache['issues']['new'], [])
        self.assertEqual(Page(html).canonicals, [url])
        self.assertIn(CANONICAL + 'category/ma/', html)
        self.assertIn(body(summaries['new']), html)
        self.assertIn(url, sitemap(data, summaries=summaries))
        self.assertIn(url, render_page(data, summaries=summaries))
        xml = rss(data, cache, summaries)
        first, fallback, _ = ElementTree.fromstring(xml).findall('channel/item')
        self.assertEqual(first.findtext('link'), url)
        self.assertEqual(first.findtext('guid'), 'sowhat-new')
        self.assertEqual(first.findtext('description'), body(summaries['new']))
        self.assertEqual(fallback.findtext('link'), CANONICAL + '2026/11/#vol-114')
        self.assertIsNone(first.find('pubDate'))
        self.assertEqual(rss(data, cache, summaries, previous=xml), xml)

    def test_rss_only_uses_verified_time_on_archive_date_in_korea(self):
        data = fixture()
        newest = data['items'][0]
        for invalid in ('2026-11-18', '2026-11-18T07:00:00', '2026-11-18T18:00:00Z'):
            self.assertIsNone(published_at(newest, {'publishedAt': invalid}))
        parser = PublishedTime()
        parser.feed('<meta property="article:modified_time" content="2026-11-18T01:00:00Z">'
                    '<meta property="article:published_time" content="2026-11-18T07:02:00Z">')
        cache = {'issues': {'new': {'publishedAt': parser.value}}}
        stamp = ElementTree.fromstring(rss(data, cache, {})).findtext('channel/item/pubDate')
        self.assertEqual(parsedate_to_datetime(stamp).isoformat(), '2026-11-18T16:02:00+09:00')


if __name__ == '__main__':
    unittest.main()
