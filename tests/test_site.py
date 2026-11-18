import json
import unittest
from html.parser import HTMLParser
from xml.etree import ElementTree

from build_site import CANONICAL, render_page, sitemap


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


if __name__ == '__main__':
    unittest.main()
