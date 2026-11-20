import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sowhat_sections


PAGE = ('<html><head><link href="/assets/css/public_email.css"></head><body>'
        '<div class="public-email"><html><head></head><body>기업 headline</body></html></div>'
        '<script>/* stibee */</script></body></html>')


class IssuePageTest(unittest.TestCase):
    def test_copy_is_noindex_bar_outside_email_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sowhat_sections, 'ISSUE_DIR', Path(tmp)):
            item = {'volume': 114, 'url': 'https://stib.ee/BsHP'}
            sowhat_sections.write_issue_page(item, PAGE)
            first = sowhat_sections.issue_path(114).read_text(encoding='utf-8')
            self.assertIn('content="noindex,follow"', first)
            self.assertIn('rel="canonical" href="https://stib.ee/BsHP"', first)
            self.assertIn('href="https://stibee.com/assets/css/public_email.css"', first)
            # the bar goes after the Stibee script, i.e. in the outer body
            self.assertGreater(first.index('swa-issue-bar"'), first.index('/* stibee */'))
            sowhat_sections.write_issue_page(item, first)
            self.assertEqual(first, sowhat_sections.issue_path(114).read_text(encoding='utf-8'))

    def test_issue_url_uses_category_slug(self):
        self.assertEqual(sowhat_sections.issue_url(114, 'ma'), 'https://sowhat.bestexit.co.kr/issue/114/#c=ma')


if __name__ == '__main__':
    unittest.main()


class ExtractTest(unittest.TestCase):
    H = '<div style="font-weight: 600; font-size: 22px; color: #1A1A1B;">{}</div>'

    def page(self, body):
        toc = '<div>M&amp;A</div><div>첫 기사</div>'
        return f'<html><body>{toc}<div> M&amp;A </div>{body}</body></html>'

    def test_two_stories_under_one_label_and_so_what_skipped(self):
        body = (self.H.format('첫 기사') + '<img src="https://img2.stibee.com/a.png">'
                + '<div>첫 기사 본문은 이렇게 충분히 길게 이어집니다.</div>' + self.H.format('SO WHAT')
                + self.H.format('두 번째 기사') + '<img src="https://img2.stibee.com/b.png">'
                + '<div>두 번째 기사 본문도 충분히 길게 이어집니다.</div>')
        got = sowhat_sections.extract(self.page(body))
        self.assertEqual([(x['n'], x['headline'], x['image'][-5:]) for x in got],
                         [(1, '첫 기사', 'a.png'), (2, '두 번째 기사', 'b.png')])

    def test_picture_above_headline(self):
        body = ('<img src="https://img2.stibee.com/a.png">' + self.H.format('첫 기사') + '<div>본문 본문 본문 본문 본문 본문</div>'
                + '<img src="https://img2.stibee.com/b.png">' + self.H.format('두 번째 기사'))
        got = sowhat_sections.extract(self.page(body))
        self.assertEqual([x['image'][-5:] for x in got], ['a.png', 'b.png'])

    def test_story_link_number(self):
        self.assertEqual(sowhat_sections.issue_url(116, 'ma', 2), 'https://sowhat.bestexit.co.kr/issue/116/#c=ma&n=2')
