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
