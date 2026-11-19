"""Fetch current weather for major Korean cities from the KMA short-term forecast API (data.go.kr).

Writes a small public JSON file (no key inside) that the archive header reads:
current temperature and precipitation type from the ultra-short-term observation,
sky state and lightning from the ultra-short-term forecast. The service key is
read from the KMA_SERVICE_KEY environment variable only.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import os
import time
import urllib.parse
import urllib.request

KST = timezone(timedelta(hours=9))
BASE = 'https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/'
# KMA 5km grid points (nx, ny) for the rolling header, in display order.
CITIES = [
    ('서울', 60, 127), ('인천', 55, 124), ('대전', 67, 100), ('광주', 58, 74),
    ('대구', 89, 90), ('울산', 102, 84), ('부산', 98, 76), ('제주', 52, 38),
]


def call(operation: str, key: str, base: datetime, rows: int, nx: int, ny: int) -> list[dict]:
    query = urllib.parse.urlencode({'serviceKey': key, 'pageNo': 1, 'numOfRows': rows, 'dataType': 'JSON', 'base_date': base.strftime('%Y%m%d'), 'base_time': base.strftime('%H%M'), 'nx': nx, 'ny': ny})
    request = urllib.request.Request(BASE + operation + '?' + query, headers={'User-Agent': 'SoWhatArchive-Weather/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.load(response)
            header = payload['response']['header']
            if header.get('resultCode') != '00':
                raise ValueError('KMA error ' + str(header.get('resultCode')))
            return payload['response']['body']['items']['item']
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3)
    return []


def observation_base(now: datetime) -> datetime:
    # Hourly observations are published about 40 minutes after the hour.
    return (now - timedelta(minutes=40)).replace(minute=0, second=0, microsecond=0)


def forecast_base(now: datetime) -> datetime:
    # Ultra-short-term forecasts are issued at HH:30 and published about 15 minutes later.
    return (now - timedelta(minutes=45)).replace(minute=30, second=0, microsecond=0)


def city_weather(key: str, now: datetime, place: str, nx: int, ny: int) -> dict:
    obs_base = observation_base(now)
    observed = {x['category']: x['obsrValue'] for x in call('getUltraSrtNcst', key, obs_base, 20, nx, ny)}
    forecast = call('getUltraSrtFcst', key, forecast_base(now), 60, nx, ny)
    first = min((x['fcstDate'] + x['fcstTime'] for x in forecast), default='')
    nearest = {x['category']: x['fcstValue'] for x in forecast if x['fcstDate'] + x['fcstTime'] == first}
    temperature = float(observed['T1H'])
    if not -50 < temperature < 50:
        raise ValueError('Unexpected temperature')
    sky = int(nearest.get('SKY', 0))
    if sky not in (1, 3, 4):
        raise ValueError('Unexpected sky state')
    return {
        'place': place,
        'temperature': round(temperature, 1),
        'pty': int(observed.get('PTY', nearest.get('PTY', 0))),
        'sky': sky,
        'lightning': 1 if float(nearest.get('LGT', 0) or 0) > 0 else 0,
        'observedAt': obs_base.isoformat(timespec='minutes'),
    }


def collect(key: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(KST)
    cities = []
    for place, nx, ny in CITIES:
        try:
            cities.append(city_weather(key, now, place, nx, ny))
        except Exception as error:  # One city failing should not hide the others.
            print(f'skip {place}: {type(error).__name__}')
        time.sleep(0.3)
    if not cities:
        raise SystemExit('No city weather could be fetched')
    return {'schemaVersion': 2, 'source': 'kma', 'updatedAt': now.isoformat(timespec='minutes'), 'cities': cities}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='weather.json')
    args = parser.parse_args()
    key = os.environ.get('KMA_SERVICE_KEY', '').strip()
    if not key:
        raise SystemExit('KMA_SERVICE_KEY is not set')
    data = collect(key)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(destination)
    print(json.dumps([(c['place'], c['temperature'], c['sky'], c['pty']) for c in data['cities']], ensure_ascii=False))


if __name__ == '__main__':
    main()
