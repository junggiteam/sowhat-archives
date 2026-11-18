"""Read-only archive checks shared by local and GitHub-hosted monitoring.

No Stibee account key, subscriber data, SMTP password, or mail recipient is stored.
Notification acknowledgments are saved only after delivery.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import urllib.request
from xml.etree import ElementTree

BASE = 'https://sowhat.bestexit.co.kr/'
ARCHIVE = 'https://page.stibee.com/archives/479387'
UPSTREAM = 'https://raw.githubusercontent.com/junggiteam/naver-news/main/data/'
ROOT = Path(__file__).resolve().parent


class ArchiveHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.link, self.text, self.items = None, [], []
        self.seed, self.in_seed = '', False
        self.canonicals, self.robots = [], ''
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and re.fullmatch(r'https://stib\.ee/[A-Za-z0-9_-]+',attrs.get('href','')):
            self.link, self.text = attrs['href'], []
        if tag == 'script' and 'data-swa-seed' in attrs:
            self.in_seed = True
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs.get('href'))
        if tag == 'meta' and attrs.get('name') == 'robots':
            self.robots = attrs.get('content','')

    def handle_data(self, data):
        if self.link:
            self.text.append(data)
        if self.in_seed:
            self.seed += data

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_seed = False
        if tag == 'a' and self.link:
            text = ' '.join(self.text)
            date = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.',text)
            if date:
                self.items.append({'id':self.link.rsplit('/',1)[-1], 'title':text[:date.start()].strip()})
            self.link = None


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)


def read_url(url):
    headers = {'User-Agent':'BestExit-ArchiveMonitor/1.0 (+https://sowhat.bestexit.co.kr/)'}
    if url.startswith('https://api.github.com/') and os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer '+os.environ['GH_TOKEN']
    request = urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(request,timeout=30) as response:
        return response.read().decode('utf-8-sig')


def collect(now):
    bucket = int(now.timestamp()//300)
    findings, values = [], {}
    endpoints = {
        'archive':ARCHIVE,
        'manifest':UPSTREAM+f'sowhat_archive.json?v={bucket}',
        'sync_status':UPSTREAM+f'sowhat_archive_status.json?v={bucket}',
        'site':BASE+f'?archive_monitor={bucket}',
        'sitemap':BASE+f'sitemap.xml?v={bucket}',
    }
    for name,url in endpoints.items():
        try:
            values[name] = read_url(url)
        except Exception as error:
            findings.append({'key':'unavailable:'+name,'message':f'{name} 접근 실패: {error}','url':url,'graceMinutes':30})
    return values, findings


def inspect(values,now):
    findings = []
    def add(key,message,url=BASE,grace=90):
        findings.append({'key':key,'message':message,'url':url,'graceMinutes':grace})
    source = ArchiveHTML(values['archive']).items if 'archive' in values else None
    if source is not None and not source:
        add('archive-format','스티비 공개 아카이브에서 발행호를 읽지 못했습니다.',ARCHIVE,30)
        source = None
    manifest = json.loads(values['manifest']) if 'manifest' in values else None
    feed = manifest.get('items',[]) if manifest else None
    site = ArchiveHTML(values['site']) if 'site' in values else None
    delivered = json.loads(site.seed) if site and site.seed else None
    for name,items in [('공통 데이터',feed),('검색용 HTML',delivered)]:
        if items is None:
            continue
        indexed = {x['id']:x for x in items}
        if source is not None:
            for item in source:
                row = indexed.get(item['id'])
                if row is None:
                    add(name+':missing:'+item['id'],f'{name}에 발행호 누락: {item["title"]}')
                elif row.get('title','').strip() != item['title']:
                    add(name+':title:'+item['id'],f'{name} 제목 미반영: {item["title"]}')
    if site:
        if site.canonicals != [BASE]:
            add('canonical','대표주소 canonical이 올바르지 않습니다.',BASE,0)
        if 'noindex' in site.robots.lower():
            add('noindex','대표 아카이브가 검색엔진 차단 상태입니다.',BASE,0)
        if delivered is None:
            add('missing-seed','공개 HTML에 검색용 발행호 데이터가 없습니다.',BASE,30)
    if feed:
        for item in feed[:2]:
            if not item.get('image'):
                add('image:'+item['id'],f'최신 발행호의 대표이미지가 비어 있습니다: {item["title"]}')
    if feed and 'sitemap' in values:
        xml = ElementTree.fromstring(values['sitemap'])
        urls = {x.text for x in xml.findall('{*}url/{*}loc')}
        expected = {BASE}|{BASE+x['date'][:7].replace('-','/')+'/' for x in feed}
        for url in sorted(expected-urls):
            add('sitemap:'+url,'사이트맵에서 아카이브 주소 누락: '+url,BASE+'sitemap.xml')
    if 'sync_status' in values:
        status = json.loads(values['sync_status'])
        if not status.get('ok'):
            add('sync-failure','스티비 자동 수집 실패: '+str(status.get('error','원인 확인 필요'))[:300],UPSTREAM+'sowhat_archive_status.json',0)
        elif status.get('checkedAt') and now-timestamp(status['checkedAt']) > timedelta(hours=6):
            add('sync-silent','공개 아카이브 자동 수집이 6시간 이상 실행되지 않았습니다.',UPSTREAM+'sowhat_archive_status.json',0)
    return findings, {'sourceCount':len(source) if source is not None else None,'feedCount':len(feed) if feed is not None else None,'htmlCount':len(delivered) if delivered is not None else None}


def check_workflows(now):
    findings, runs = [], []
    for repo,workflow in [('naver-news','sowhat_archive.yml'),('sowhat-archives','refresh.yml')]:
        url = f'https://api.github.com/repos/junggiteam/{repo}/actions/workflows/{workflow}/runs?per_page=1&status=completed'
        try:
            data = json.loads(read_url(url))
            run = data.get('workflow_runs',[None])[0]
            if run is None:
                raise ValueError('완료된 실행 기록이 없습니다.')
            runs.append({'repository':repo,'conclusion':run['conclusion'],'url':run['html_url'],'createdAt':run['created_at']})
            if run['conclusion'] in {'failure','timed_out','action_required','stale'}:
                findings.append({'key':'workflow:'+repo,'message':f'{repo} 자동 갱신 작업 실패 ({run["conclusion"]})','url':run['html_url'],'graceMinutes':0})
            if repo == 'sowhat-archives' and now-timestamp(run['created_at']) > timedelta(hours=6):
                findings.append({'key':'workflow-silent:'+repo,'message':'검색용 HTML 자동 갱신이 6시간 이상 실행되지 않았습니다.','url':run['html_url'],'graceMinutes':0})
        except Exception as error:
            findings.append({'key':'workflow-unavailable:'+repo,'message':f'{repo} 실행 상태 확인 불가: {error}','url':url,'graceMinutes':30})
    return findings,runs


def update_state(state,findings,now):
    incidents, alertable = {}, []
    for finding in findings:
        previous = state.get('incidents',{}).get(finding['key'],{})
        first = previous.get('firstSeen',now.isoformat())
        record = {**finding,'firstSeen':first,'lastSeen':now.isoformat()}
        incidents[finding['key']] = record
        if now-timestamp(first) >= timedelta(minutes=finding['graceMinutes']):
            alertable.append(record)
    prior = state.get('lastDeliveredFingerprint','')
    fingerprint = sha256('|'.join(sorted(x['key'] for x in alertable)).encode()).hexdigest() if alertable else 'healthy'
    event = 'problem' if alertable else ('recovery' if not findings and prior not in ('','healthy') else None)
    delivery_required = event is not None and fingerprint != prior
    state.update(incidents=incidents,lastCheckedAt=now.isoformat())
    return {'status':'problem' if alertable else ('pending' if findings else 'healthy'),'event':event,'emailRequired':delivery_required,'fingerprint':fingerprint,'issues':alertable,'pending':[x for x in incidents.values() if x not in alertable]}


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def run_check(state, now=None):
    now = now or datetime.now(timezone.utc)
    values, findings = collect(now)
    try:
        content_findings, counts = inspect(values,now)
        findings += content_findings
    except Exception as error:
        counts = {}
        findings.append({'key':'monitor-parse','message':'점검 데이터 해석 실패: '+str(error),'url':BASE,'graceMinutes':0})
    jobs, runs = check_workflows(now)
    report = update_state(state,findings+jobs,now)
    report.update(checkedAt=now.isoformat(),counts=counts,workflows=runs,site=BASE)
    if report['emailRequired']:
        pending = state.get('pendingDelivery',{})
        if pending.get('fingerprint') != report['fingerprint']:
            pending = {'fingerprint':report['fingerprint'],'id':sha256((report['fingerprint']+now.isoformat()).encode()).hexdigest()[:24]}
        state['pendingDelivery'] = pending
        report['notificationId'] = pending['id']
        report['emailSubject'] = '[쏘왓레터] '+('자동 갱신 이상 감지' if report['event']=='problem' else '자동 갱신 정상 복구')
        report['emailBody'] = '\n'.join([report['emailSubject'],'사이트: '+BASE,'점검 시각(한국): '+now.astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M'),'알림 ID: '+pending['id'],'',*sum(([x['message'],x['url'],''] for x in report['issues']),[]), '동일한 이상 상태는 중복 알리지 않으며, 정상 복구 시 한 번 안내합니다.'])
    state['lastReport'] = report
    return report


def acknowledge(state, fingerprint):
    if fingerprint != state.get('lastReport',{}).get('fingerprint'):
        raise ValueError('발송 확인 대상이 최근 점검 결과와 다릅니다.')
    state['lastDeliveredFingerprint'] = fingerprint
    state.pop('pendingDelivery',None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state',type=Path,default=ROOT/'.monitor/state.json')
    parser.add_argument('--ack-notification')
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding='utf-8')) if args.state.exists() else {}
    if args.ack_notification:
        acknowledge(state,args.ack_notification)
        save(args.state,state)
        print(json.dumps({'deliveryAcknowledged':True}))
        return
    report = run_check(state)
    save(args.state,state)
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
