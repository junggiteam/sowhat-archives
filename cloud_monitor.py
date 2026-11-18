"""GitHub-hosted checks and Gmail SMTP alerts. Python standard library only.

Secrets are injected by Actions, never stored in the public state branch.
No AI calls, artifact uploads, caches, external database, or paid mail service.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, parseaddr
import html
import json
import os
from pathlib import Path
import re
import smtplib
import ssl
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from monitor_archive import BASE, acknowledge, run_check

STATE_BRANCH = 'monitor-state'
STATE_FILE = 'state.json'


class GitHubState:
    def __init__(self, repository, token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
            raise ValueError('Invalid GitHub repository')
        if not token:
            raise ValueError('GH_TOKEN is required')
        self.base = 'https://api.github.com/repos/'+repository
        self.token = token
        self.sha = None
        self.new_branch = False

    def request(self, method, path, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        request = Request(self.base+path,data=payload,method=method,headers={
            'Authorization':'Bearer '+self.token,
            'Accept':'application/vnd.github+json',
            'X-GitHub-Api-Version':'2022-11-28',
            'Content-Type':'application/json',
            'User-Agent':'BestExit-ArchiveMonitor/1.0',
        })
        with urlopen(request,timeout=30) as response:
            return json.load(response)

    def load(self):
        try:
            result = self.request('GET','/contents/'+STATE_FILE+'?ref='+STATE_BRANCH)
        except HTTPError as error:
            if error.code != 404:
                raise
            # A missing branch is a first run. Other errors must not reset history.
            try:
                self.request('GET','/git/ref/heads/'+STATE_BRANCH)
            except HTTPError as branch_error:
                if branch_error.code != 404:
                    raise
                self.new_branch = True
                return {}
            raise RuntimeError('State branch exists but state.json is missing') from error
        self.sha = result['sha']
        state = json.loads(base64.b64decode(result['content']).decode('utf-8'))
        if not isinstance(state,dict):
            raise ValueError('State must be an object')
        return state

    def save(self, state):
        content = json.dumps(state,ensure_ascii=False,indent=2)+'\n'
        message = 'Record archive monitor state'
        if self.new_branch:
            # An orphan branch holds only public operational state, never site files.
            tree = self.request('POST','/git/trees',{'tree':[
                {'path':STATE_FILE,'mode':'100644','type':'blob','content':content}
            ]})
            commit = self.request('POST','/git/commits',{
                'message':message,'tree':tree['sha'],'parents':[],
            })
            self.request('POST','/git/refs',{
                'ref':'refs/heads/'+STATE_BRANCH,'sha':commit['sha'],
            })
            self.sha = tree['tree'][0]['sha']
            self.new_branch = False
            return
        result = self.request('PUT','/contents/'+STATE_FILE,{
            'message':message,'branch':STATE_BRANCH,'sha':self.sha,
            'content':base64.b64encode(content.encode()).decode(),
        })
        self.sha = result['content']['sha']


def mail_settings(environ):
    required = ('SOWHAT_SMTP_USERNAME','SOWHAT_SMTP_PASSWORD','SOWHAT_ALERT_TO')
    missing = [name for name in required if not environ.get(name,'').strip()]
    if missing:
        raise ValueError('Missing repository secrets: '+', '.join(missing))
    sender = environ['SOWHAT_SMTP_USERNAME'].strip()
    recipient = environ['SOWHAT_ALERT_TO'].strip()
    for address in (sender,recipient):
        if '\r' in address or '\n' in address or parseaddr(address)[1] != address or not re.fullmatch(r'[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+',address):
            raise ValueError('Mail settings must contain one email address each')
    if not sender.lower().endswith('@gmail.com'):
        raise ValueError('This sender uses Gmail SMTP')
    password = ''.join(environ['SOWHAT_SMTP_PASSWORD'].split())
    if not re.fullmatch(r'[A-Za-z]{16}',password):
        raise ValueError('Use a 16-letter Google app password')
    return sender,recipient,password


def send_mail(settings, subject, body, notification_id):
    sender,recipient,password = settings
    message = EmailMessage()
    message['From'] = sender
    message['To'] = recipient
    message['Subject'] = subject
    message['Date'] = format_datetime(datetime.now(timezone.utc))
    message['Message-ID'] = '<sowhat-'+notification_id+'@sowhat.bestexit.co.kr>'
    message.set_content(body)
    message.add_alternative('<html><body><pre style="white-space:pre-wrap;font-family:sans-serif">'
        +html.escape(body)+'</pre></body></html>',subtype='html')
    with smtplib.SMTP_SSL('smtp.gmail.com',465,context=ssl.create_default_context(),timeout=30) as smtp:
        smtp.login(sender,password)
        refused = smtp.send_message(message)
        if refused:
            raise RuntimeError('SMTP did not accept the recipient')


def setup_message(report, run_id):
    subject = '[쏘왓레터] GitHub 무인 점검·이메일 연결 테스트'
    counts = report.get('counts',{})
    body = '\n'.join([
        '이 메일은 GitHub Actions 실행기에서 Gmail SMTP로 직접 보낸 연결 확인 메일입니다.',
        '사이트: '+BASE,
        '점검 상태: '+report['status'],
        '스티비 / 공통 데이터 / 검색용 HTML 발행호 수: '
        +' / '.join(str(counts.get(key,'확인 불가')) for key in ('sourceCount','feedCount','htmlCount')),
        '',
        '컴퓨터와 Codex 앱을 꺼도 GitHub에서 매시간 10분에 점검합니다.',
        'GitHub 예약 실행은 혼잡 시 지연될 수 있습니다.',
        'AI 모델·OpenAI API·Codex 토큰을 사용하지 않습니다.',
        '공개 저장소의 표준 Linux 실행기만 사용하며 유료 메일 서비스를 사용하지 않습니다.',
        '',
        '발행 일정: 한국시간 월~금 15:30~16:30, 토·일·공휴일 미발행.',
        '스티비에 실제 공개된 발행호를 비교하므로 쉬는 날의 미발행은 누락 경고 대상이 아닙니다.',
        '발행호·제목·SEO 미반영은 최초 발견 후 90분, 일시적인 접근 오류는 30분 유예합니다.',
        '갱신 실패·장시간 실행 중단·누락·정상 복구 시 알립니다.',
        '',
        '연결 확인 ID: cloud-setup-'+run_id,
    ])
    return subject,body,'cloud-setup-'+run_id


def execute(store, environ, *, test_email=False, check=run_check, deliver=send_mail):
    state = store.load()
    report = check(state)
    # Persist the grace clock and notification ID before any delivery attempt.
    store.save(state)
    summary = {'status':report['status'],'counts':report.get('counts',{}),
        'emailRequired':report['emailRequired'],'alertSent':False,'testEmailSent':False}
    try:
        settings = mail_settings(environ)
        if report['emailRequired']:
            deliver(settings,report['emailSubject'],report['emailBody'],report['notificationId'])
            acknowledge(state,report['fingerprint'])
            store.save(state)
            summary['alertSent'] = True
        run_id = environ.get('GITHUB_RUN_ID','manual')
        if test_email and state.get('lastSetupTestRunId') != run_id:
            deliver(settings,*setup_message(report,run_id))
            state['lastSetupTestRunId'] = run_id
            store.save(state)
            summary['testEmailSent'] = True
    except Exception as error:
        # Never print SMTP responses, addresses, passwords, or tokens.
        summary['mailError'] = type(error).__name__
        if isinstance(error,ValueError):
            summary['configurationError'] = str(error)
        write_summary(summary)
        return 1
    write_summary(summary)
    return 0


def write_summary(result):
    print(json.dumps(result,ensure_ascii=False))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(
            '## Archive monitor\n\n'
            +'\n'.join('    '+line for line in json.dumps(result,ensure_ascii=False,indent=2).splitlines())
            +'\n',encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-email',action='store_true')
    args = parser.parse_args()
    try:
        store = GitHubState(os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GH_TOKEN',''))
        return execute(store,os.environ,test_email=args.test_email)
    except Exception as error:
        write_summary({'monitorError':type(error).__name__})
        return 1


if __name__ == '__main__':
    sys.exit(main())
