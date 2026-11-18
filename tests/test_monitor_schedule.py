from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from monitor_schedule import KST, ROOT, decision, load_holidays, parse_holidays


def at(value):
    return datetime.fromisoformat(value).replace(tzinfo=KST)


def fixture():
    rows = [
        ('신정','1월 1일'),('설날','2월16일~ 2월18일'),
        ('3.1절','3월 1일'),('어린이날','5월 5일'),
        ('부처님오신날','5월 24일'),('현충일','6월 6일'),
        ('제헌절','7월 17일'),('광복절','8월 15일'),
        ('추석','9월24일~ 9월26일'),('개천절','10월 3일'),
        ('한글날','10월 9일'),('기독탄신일','12월 25일'),
        ('공휴일이 아닌 기념일**','11월 18일'),
    ]
    return '<h2>2026년 달력자료</h2><h2>국경일과 공휴일</h2><table>'+''.join(
        '<tr><td>'+name+'</td><td>'+date+'<br>(요일)</td></tr>'
        for name,date in rows)+'</table><h2>기념일</h2><table><tr><td>보통 날</td><td>11월 19일</td></tr></table>'


class MonitorScheduleTests(unittest.TestCase):
    def test_weekends_and_off_hours_do_not_even_fetch_calendar(self):
        loader = Mock(side_effect=AssertionError('calendar must not be called'))
        for value in ['2026-11-21T16:00','2026-11-22T16:00',
                      '2026-11-18T14:59','2026-11-18T17:01','2026-11-18T23:00']:
            self.assertFalse(decision(at(value),loader)['allowed'])
        loader.assert_not_called()

    def test_korean_15_to_17_boundaries_and_utc_conversion(self):
        loader = lambda year:{}
        for value in ['2026-11-18T15:00','2026-11-18T16:10','2026-11-18T16:50','2026-11-18T17:00']:
            self.assertTrue(decision(at(value),loader)['allowed'])
        utc = datetime(2026,11,18,6,10,tzinfo=timezone.utc)
        self.assertTrue(decision(utc,loader)['allowed'])

    def test_actual_holidays_and_substitutes_are_skipped(self):
        years = json.loads((ROOT/'data/kr-public-holidays.json').read_text(encoding='utf-8'))['years']
        loader = lambda year:years[str(year)]
        for value in ['2026-12-25T16:10','2026-02-17T16:10',
                      '2026-06-03T16:10','2026-05-01T16:10',
                      '2027-02-09T16:10','2027-07-19T16:10']:
            result = decision(at(value),loader)
            self.assertFalse(result['allowed'])
            self.assertEqual(result['reason'],'public-holiday')
        self.assertTrue(decision(at('2026-11-18T16:10'),loader)['allowed'])

    def test_calendar_parser_expands_lunar_ranges_and_ignores_observances(self):
        days = parse_holidays(fixture(),2026)
        for day in ['2026-02-16','2026-02-17','2026-02-18',
                    '2026-09-24','2026-09-25','2026-09-26']:
            self.assertIn(day,days)
        self.assertNotIn('2026-11-18',days)
        self.assertNotIn('2026-11-19',days)
        self.assertIn('2026-05-01',days)

    def test_wrong_year_or_broken_calendar_is_not_treated_as_no_holidays(self):
        for document,year in [(fixture(),2027),('<h2>2026년 달력자료</h2>',2026)]:
            with self.assertRaises(ValueError):
                parse_holidays(document,year)

    def test_calendar_outage_uses_verified_snapshot_but_not_unknown_year(self):
        with patch('monitor_schedule.urlopen',side_effect=OSError('offline')):
            self.assertIn('2027-02-09',load_holidays(2027))
            with self.assertRaises(ValueError):
                load_holidays(2099)


if __name__ == '__main__':
    unittest.main()
