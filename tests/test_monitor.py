from datetime import datetime, timedelta, timezone
import json
import unittest
from monitor_archive import BASE, inspect, update_state


NOW = datetime(2026,11,18,8,tzinfo=timezone.utc)


def values():
    item = {'id':'new','title':'새 호 제목','date':'2026-11-18','image':'https://img2.stibee.com/cover.jpg'}
    return {'archive':'<a href="https://stib.ee/new"><span>새 호 제목</span>2026. 11. 18.</a>',
        'manifest':json.dumps({'items':[item]}),
        'site':'<link rel="canonical" href="'+BASE+'"><meta name="robots" content="index,follow"><script data-swa-seed type="application/json">'+json.dumps([item])+'</script>',
        'sync_status':json.dumps({'ok':True,'checkedAt':NOW.isoformat()}),
        'sitemap':'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+BASE+'</loc></url><url><loc>'+BASE+'2026/11/</loc></url></urlset>'}


class MonitorTests(unittest.TestCase):
    def test_healthy_source_feed_html_and_sitemap(self):
        issues,counts = inspect(values(),NOW)
        self.assertEqual(issues,[])
        self.assertEqual(counts,{'sourceCount':1,'feedCount':1,'htmlCount':1})

    def test_missing_new_issue_is_detected_but_has_grace(self):
        data = values()
        data['manifest'] = '{"items":[]}'
        issues,_ = inspect(data,NOW)
        self.assertTrue(any('missing:new' in x['key'] for x in issues))
        state = {}
        self.assertFalse(update_state(state,issues,NOW)['emailRequired'])
        self.assertTrue(update_state(state,issues,NOW+timedelta(minutes=91))['emailRequired'])

    def test_delivered_problem_is_not_sent_again_and_recovery_is_once(self):
        issue = {'key':'sync-failure','message':'실패','url':BASE,'graceMinutes':0}
        state = {}
        first = update_state(state,[issue],NOW)
        self.assertTrue(first['emailRequired'])
        state['lastDeliveredFingerprint'] = first['fingerprint']
        self.assertFalse(update_state(state,[issue],NOW+timedelta(hours=1))['emailRequired'])
        recovered = update_state(state,[],NOW+timedelta(hours=2))
        self.assertEqual(recovered['event'],'recovery')
        self.assertTrue(recovered['emailRequired'])
        state['lastDeliveredFingerprint'] = recovered['fingerprint']
        self.assertFalse(update_state(state,[],NOW+timedelta(hours=3))['emailRequired'])

    def test_delivery_failure_can_be_retried_without_early_ack(self):
        issue = {'key':'failed','message':'실패','url':BASE,'graceMinutes':0}
        state = {}
        self.assertTrue(update_state(state,[issue],NOW)['emailRequired'])
        self.assertTrue(update_state(state,[issue],NOW+timedelta(hours=1))['emailRequired'])

    def test_missing_image_sitemap_and_noindex_are_detected(self):
        data = values()
        payload = json.loads(data['manifest'])
        payload['items'][0]['image'] = ''
        data['manifest'] = json.dumps(payload)
        data['sitemap'] = '<urlset/>'
        data['site'] = data['site'].replace('index,follow','noindex,nofollow')
        keys = {x['key'] for x in inspect(data,NOW)[0]}
        self.assertIn('image:new',keys)
        self.assertIn('noindex',keys)
        self.assertTrue(any(x.startswith('sitemap:') for x in keys))

    def test_parser_failure_does_not_fake_missing_every_issue(self):
        data = values()
        data['archive'] = '<h1>source unavailable</h1>'
        issues,_ = inspect(data,NOW)
        self.assertIn('archive-format',{x['key'] for x in issues})
        self.assertFalse(any(':missing:' in x['key'] for x in issues))


if __name__ == '__main__':
    unittest.main()
