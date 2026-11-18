"""Skip archive checks outside publication hours and on Korean holidays."""
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent
CALENDAR_URL = 'https://astro.kasi.re.kr/kor/life/post/calendarData?search_year='


class HolidayTable(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.heading, self.target, self.inside, self.done = None, False, False, False
        self.cell, self.row, self.rows = None, [], []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.heading = []
        if tag == 'table' and self.target and not self.done:
            self.inside = True
        if self.inside and tag == 'tr':
            self.row = []
        if self.inside and tag == 'td':
            self.cell = []
        if tag == 'br' and self.cell is not None:
            self.cell.append(' ')

    def handle_data(self, data):
        if self.heading is not None:
            self.heading.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == 'h2' and self.heading is not None:
            self.target = ''.join(self.heading).strip() == '국경일과 공휴일'
            self.heading = None
        if tag == 'td' and self.cell is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell = None
        if tag == 'tr' and self.inside and self.row:
            self.rows.append(self.row)
        if tag == 'table' and self.inside:
            self.inside, self.done = False, True


def parse_holidays(document, year):
    if not re.search(str(year)+r'년\s*달력자료',document):
        raise ValueError('Calendar year does not match requested year')
    table = HolidayTable(document)
    days = {}
    for row in table.rows:
        if len(row) % 2:
            raise ValueError('Unexpected holiday table format')
        for index in range(0,len(row),2):
            name, text = row[index:index+2]
            if not name or not text or '**' in name or '**' in text:
                continue
            matches = re.findall(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일',text)
            if not 1 <= len(matches) <= 2:
                raise ValueError('Invalid holiday date')
            first = date(year,*map(int,matches[0]))
            last = date(year,*map(int,matches[-1]))
            if not 0 <= (last-first).days <= 6:
                raise ValueError('Unexpected holiday range')
            while first <= last:
                days[first.isoformat()] = name.replace('*','').strip()
                first += timedelta(days=1)
    # KASI's older 2026 table predates this addition, confirmed by KASA's 2027 notice.
    if year == 2026:
        days['2026-05-01'] = '노동절'
    if len(days) < 15 or f'{year}-01-01' not in days or f'{year}-12-25' not in days:
        raise ValueError('Incomplete Korean holiday calendar')
    return days


def load_holidays(year):
    try:
        request = Request(CALENDAR_URL+str(year),headers={'User-Agent':'BestExit-ArchiveMonitor/1.0'})
        with urlopen(request,timeout=12) as response:
            return parse_holidays(response.read().decode('utf-8'),year)
    except Exception:
        snapshot = json.loads((ROOT/'data/kr-public-holidays.json').read_text(encoding='utf-8'))
        days = snapshot['years'].get(str(year))
        if not days:
            raise ValueError('No verified Korean holiday calendar for this year')
        return days


def decision(now, holiday_loader=load_holidays):
    local = now.astimezone(KST)
    result = {'allowed':False,'localTime':local.isoformat()}
    if local.weekday() >= 5:
        return {**result,'reason':'weekend'}
    # Only three cron slots exist; allow up to 30 minutes of delay for 17:30.
    if not 16*60 <= local.hour*60+local.minute <= 18*60:
        return {**result,'reason':'outside-16-to-18-delay-window'}
    days = holiday_loader(local.year)
    name = days.get(local.date().isoformat())
    if name:
        return {**result,'reason':'public-holiday','holiday':name}
    return {**result,'allowed':True,'reason':'publication-hours'}


def main():
    if os.environ.get('BYPASS_SCHEDULE') == 'true':
        result = {'allowed':True,'reason':'explicit-manual-mail-test'}
    else:
        result = decision(datetime.now(timezone.utc))
    print(json.dumps(result,ensure_ascii=False))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as output:
            output.write('allowed='+str(result['allowed']).lower()+'\n')
    if os.environ.get('GITHUB_STEP_SUMMARY') and not result['allowed']:
        Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(
            'Archive check skipped: '+result['reason']+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
