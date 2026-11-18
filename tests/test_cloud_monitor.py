import base64
from copy import deepcopy
from datetime import timedelta
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from cloud_monitor import GitHubState, execute, mail_settings, send_mail
from monitor_archive import run_check
from test_monitor import NOW, values

ENV = {'SOWHAT_SMTP_USERNAME':'operator@gmail.com',
    'SOWHAT_SMTP_PASSWORD':'abcd efgh ijkl mnop',
    'SOWHAT_ALERT_TO':'recipient@example.com','GITHUB_RUN_ID':'1234'}


class MemoryState:
    def __init__(self):
        self.state = {}
        self.saved = []

    def load(self):
        return deepcopy(self.state)

    def save(self,state):
        self.state = deepcopy(state)
        self.saved.append(deepcopy(state))


def check_at(now,data=None):
    def check(state):
        with patch('monitor_archive.collect',return_value=(data or values(),[])), \
             patch('monitor_archive.check_workflows',return_value=([],[])):
            return run_check(state,now)
    return check


class CloudMonitorTests(unittest.TestCase):
    def setUp(self):
        self.stdout = patch('sys.stdout',new_callable=io.StringIO)
        self.stdout.start()
        self.addCleanup(self.stdout.stop)

    def test_healthy_run_needs_no_mail_and_saves_remote_state(self):
        store, sent = MemoryState(), []
        result = execute(store,ENV,check=check_at(NOW),deliver=lambda *args:sent.append(args))
        self.assertEqual(result,0)
        self.assertEqual(sent,[])
        self.assertEqual(store.state['lastReport']['counts']['sourceCount'],1)
        self.assertNotIn(ENV['SOWHAT_SMTP_USERNAME'],json.dumps(store.state))
        self.assertNotIn(ENV['SOWHAT_SMTP_PASSWORD'],json.dumps(store.state))

    def test_missing_issue_grace_survives_fresh_runners_and_recovery_sends_once(self):
        store, sent = MemoryState(), []
        data = values()
        data['manifest'] = '{"items":[]}'
        deliver = lambda *args:sent.append(args)
        execute(store,ENV,check=check_at(NOW,data),deliver=deliver)
        self.assertEqual(sent,[])
        execute(store,ENV,check=check_at(NOW+timedelta(minutes=91),data),deliver=deliver)
        self.assertEqual(len(sent),1)
        execute(store,ENV,check=check_at(NOW+timedelta(minutes=120),data),deliver=deliver)
        self.assertEqual(len(sent),1)
        execute(store,ENV,check=check_at(NOW+timedelta(minutes=150)),deliver=deliver)
        self.assertEqual(len(sent),2)
        self.assertIn('정상 복구',sent[-1][1])
        execute(store,ENV,check=check_at(NOW+timedelta(minutes=180)),deliver=deliver)
        self.assertEqual(len(sent),2)

    def test_failed_smtp_is_not_acknowledged_and_notification_id_is_reused(self):
        store, sent = MemoryState(), []
        data = values()
        data['sync_status'] = '{"ok":false,"error":"test"}'
        def failed(*args):
            sent.append(args)
            raise RuntimeError('Do not log private server responses')
        result = execute(store,ENV,check=check_at(NOW,data),deliver=failed)
        self.assertEqual(result,1)
        self.assertNotIn('lastDeliveredFingerprint',store.state)
        self.assertNotIn('private server',sys_stdout())
        execute(store,ENV,check=check_at(NOW+timedelta(hours=1),data),
            deliver=lambda *args:sent.append(args))
        self.assertEqual(sent[0][-1],sent[1][-1])
        self.assertNotIn('pendingDelivery',store.state)

    def test_missing_credentials_cannot_report_mail_ready(self):
        store = MemoryState()
        result = execute(store,{},check=check_at(NOW),
            deliver=lambda *args:self.fail('must not send'))
        self.assertEqual(result,1)
        self.assertIn('Missing repository secrets',sys_stdout())

    def test_setup_test_is_sent_from_runner_once_without_changing_incident_ack(self):
        store, sent = MemoryState(), []
        for _ in range(2):
            execute(store,ENV,test_email=True,check=check_at(NOW),
                deliver=lambda *args:sent.append(args))
        self.assertEqual(len(sent),1)
        self.assertIn('GitHub 무인',sent[0][1])
        self.assertEqual(store.state['lastSetupTestRunId'],'1234')
        self.assertNotIn('lastDeliveredFingerprint',store.state)

    def test_gmail_app_password_spaces_and_single_recipient_validation(self):
        self.assertEqual(mail_settings(ENV)[-1],'abcdefghijklmnop')
        for value in ['a@example.com,b@example.com','a@example.com\nBcc: b@example.com']:
            with self.assertRaises(ValueError):
                mail_settings({**ENV,'SOWHAT_ALERT_TO':value})

    def test_tls_smtp_sends_escaped_html_and_fixed_message_id(self):
        with patch('cloud_monitor.smtplib.SMTP_SSL') as smtp:
            client = smtp.return_value.__enter__.return_value
            client.send_message.return_value = {}
            send_mail(mail_settings(ENV),'제목','<script>unsafe</script>','test-123')
            smtp.assert_called_once()
            self.assertEqual(smtp.call_args.args,('smtp.gmail.com',465))
            self.assertTrue(smtp.call_args.kwargs['context'].check_hostname)
            message = client.send_message.call_args.args[0]
            self.assertEqual(message['To'],ENV['SOWHAT_ALERT_TO'])
            self.assertIn('test-123',message['Message-ID'])
            self.assertIn('&lt;script&gt;',message.get_body('html').get_content())

    def test_github_outage_does_not_reset_grace_or_delivery_history(self):
        store = GitHubState('owner/repo','test-token')
        with patch.object(store,'request',side_effect=HTTPError('url',403,'blocked',{},None)):
            with self.assertRaises(HTTPError):
                store.load()
        self.assertFalse(store.new_branch)

    def test_first_run_creates_state_only_orphan_branch_then_updates_blob_sha(self):
        store = GitHubState('owner/repo','test-token')
        missing = HTTPError('url',404,'missing',{},None)
        with patch.object(store,'request',side_effect=missing):
            self.assertEqual(store.load(),{})
        with patch.object(store,'request',side_effect=[
            {'sha':'tree','tree':[{'path':'state.json','sha':'blob1'}]},
            {'sha':'commit'}, {'ref':'refs/heads/monitor-state'},
            {'content':{'sha':'blob2'}},
        ]) as request:
            store.save({'lastCheckedAt':'first'})
            self.assertEqual(request.call_args_list[1].args[2]['parents'],[])
            self.assertEqual(len(request.call_args_list[0].args[2]['tree']),1)
            store.save({'lastCheckedAt':'second'})
            payload = request.call_args.args[2]
            self.assertEqual(payload['sha'],'blob1')
            self.assertEqual(json.loads(base64.b64decode(payload['content'])),
                {'lastCheckedAt':'second'})
            self.assertEqual(store.sha,'blob2')


def sys_stdout():
    import sys
    return sys.stdout.getvalue()


if __name__ == '__main__':
    unittest.main()
