"""Read public end-of-day data only. No broker credentials or trading endpoints."""
import argparse
import csv
import io
import json
import math
from datetime import date, datetime, timedelta, time, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
IST = ZoneInfo('Asia/Kolkata')
NY = ZoneInfo('America/New_York')

def download(url):
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'}), timeout=30) as response:
        return response.read()

def number(value):
    try:
        result = float(str(value).replace(',', ''))
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None

def parse_date(value):
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d-%b-%Y'):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError('Unrecognised source date: ' + value)

def index_rows(payload, session):
    rows = list(csv.DictReader(io.StringIO(payload.decode('utf-8-sig'))))
    result = {}
    for row in rows:
        name = row.get('Index Name', '').strip().upper()
        if name in ('NIFTY 50', 'INDIA VIX'):
            if parse_date(row['Index Date']) != session:
                raise ValueError('Index report date does not match requested session')
            key = 'nifty' if name == 'NIFTY 50' else 'vix'
            value = number(row.get('Closing Index Value', row.get('Closing')))
            if value is None or value <= 0:
                raise ValueError('Invalid closing value for ' + name)
            result[key] = value
            # NSE supplies the comparison with the actual previous trading close.
            result[key + '_points'] = number(row.get('Points Change'))
            pct = number(row.get('Change(%)'))
            result[key + '_pct'] = pct / 100 if pct is not None else None
    if set(('nifty', 'vix')) - result.keys():
        raise ValueError('Nifty 50 or India VIX is missing from index report')
    return result

def option_rows(payload, session):
    with ZipFile(io.BytesIO(payload)) as z:
        names = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(names) != 1:
            raise ValueError('Unexpected bhavcopy archive')
        rows = csv.DictReader(io.StringIO(z.read(names[0]).decode('utf-8-sig')))
        totals = {}
        contracts = set()
        for row in rows:
            if row.get('TckrSymb') != 'NIFTY' or row.get('OptnTp') not in ('PE', 'CE'):
                continue
            if parse_date(row['TradDt']) != session:
                raise ValueError('Options report date does not match requested session')
            expiry = parse_date(row.get('FininstrmActlXpryDt') or row['XpryDt'])
            if expiry < session:
                continue
            identity = row['FinInstrmId']
            if identity in contracts:
                raise ValueError('Duplicate options contract in bhavcopy')
            contracts.add(identity)
            oi = number(row.get('OpnIntrst'))
            if oi is None or oi < 0:
                raise ValueError('Missing/invalid open interest')
            # Preserve the exchange's reported OI quantity. Do not infer lots
            # from lot-size metadata during exchange lot-size transitions.
            bucket = totals.setdefault(expiry, {'PE': 0.0, 'CE': 0.0})
            bucket[row['OptnTp']] += oi
    if not totals:
        raise ValueError('No NIFTY options in bhavcopy')
    nearest = min(totals)
    all_put = sum(v['PE'] for v in totals.values())
    all_call = sum(v['CE'] for v in totals.values())
    if all_call <= 0 or totals[nearest]['CE'] <= 0:
        raise ValueError('Zero call OI denominator')
    return {'expiry': nearest.isoformat(), 'near_put': totals[nearest]['PE'],
            'near_call': totals[nearest]['CE'], 'all_put': all_put, 'all_call': all_call}

def yahoo_rows(payload, symbol, now):
    doc = json.loads(payload)['chart']
    if doc.get('error') or not doc.get('result'):
        raise ValueError('Yahoo chart source returned no results')
    block = doc['result'][0]
    if block['meta']['symbol'] != symbol:
        raise ValueError('Unexpected Yahoo instrument')
    closes = block['indicators']['quote'][0]['close']
    result = {}
    for stamp, close in zip(block.get('timestamp', []), closes):
        session = datetime.fromtimestamp(stamp, NY).date()
        # Wait until after the regular close even on early-close days.
        cutoff = datetime.combine(session, time(16, 20), NY)
        value = number(close)
        if now >= cutoff and value is not None and value > 0:
            result[session.isoformat()] = round(value, 2)
    return result

def fred_rows(payload):
    result = {'nasdaq': {}, 'dow': {}}
    for row in csv.DictReader(io.StringIO(payload.decode('utf-8-sig'))):
        session = row.get('observation_date', row.get('DATE'))
        if not session:
            raise ValueError('Missing FRED observation date')
        for key, series in [('nasdaq', 'NASDAQCOM'), ('dow', 'DJIA')]:
            value = number(row.get(series))
            if value is not None and value > 0:
                result[key][session] = value
    return result

def candidates(end, days):
    return [end - timedelta(days=n) for n in reversed(range(days))
            if (end - timedelta(days=n)).weekday() < 5]

def update(history, now, fetch=download, days=10):
    errors = []
    stamp = now.astimezone(IST).isoformat(timespec='seconds')
    local = now.astimezone(IST)
    india_end = local.date() if local.time() >= time(18) else local.date() - timedelta(days=1)
    for session in candidates(india_end, days):
        key = session.isoformat()
        row = history['india'].setdefault(key, {})
        messages = []
        indices = f'https://nsearchives.nseindia.com/content/indices/ind_close_all_{session:%d%m%Y}.csv'
        options = f'https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{session:%Y%m%d}_F_0000.csv.zip'
        for fields, url, parser, sourcekey in [
            (('nifty', 'vix'), indices, index_rows, 'indices_source'),
            (('near_put', 'near_call', 'all_put', 'all_call'), options, option_rows, 'options_source')]:
            if all(row.get(f) is not None for f in fields):
                continue
            try:
                row.update(parser(fetch(url), session))
                row[sourcekey] = url
                row['updated_at'] = stamp
            except Exception as exc:
                messages.append(sourcekey + ': ' + str(exc))
        missing = [f for f in ('nifty', 'vix', 'near_put', 'near_call', 'all_put', 'all_call') if row.get(f) is None]
        row['status'] = 'Complete' if not missing else 'Unavailable: ' + ', '.join(missing) + ' (holiday or report pending/error)'
        row['detail'] = ' | '.join(messages)
        if missing:
            errors.append('India ' + key + ': ' + row['status'])

    ny_now = now.astimezone(NY)
    us_end = ny_now.date() if ny_now.time() >= time(16, 20) else ny_now.date() - timedelta(days=1)
    us_data, source_errors = {}, []
    for name, symbol in [('nasdaq', '^IXIC'), ('dow', '^DJI')]:
        url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + symbol.replace('^', '%5E') + '?range=1mo&interval=1d'
        try:
            us_data[name] = (yahoo_rows(fetch(url), symbol, now), url)
        except Exception as exc:
            us_data[name] = ({}, url)
            source_errors.append(name + ': ' + str(exc))
    fred_url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQCOM,DJIA'
    fred = {'nasdaq': {}, 'dow': {}}
    if any(any(s.isoformat() not in us_data[n][0] for s in candidates(us_end, days)) for n in us_data):
        try:
            fred = fred_rows(fetch(fred_url))
        except Exception as exc:
            source_errors.append('FRED: ' + str(exc))
    for session in candidates(us_end, days):
        key = session.isoformat()
        row = history['us'].setdefault(key, {})
        for name in ('nasdaq', 'dow'):
            values, url = us_data[name]
            value = values.get(key)
            if value is None:
                value, url = fred[name].get(key), fred_url
            # Preserve an already verified close if a later fetch fails.
            if value is not None and (row.get(name) != value or row.get(name + '_source') != url):
                row[name] = value
                row[name + '_source'] = url
                row['updated_at'] = stamp
            if value is not None:
                series = values if key in values else fred[name]
                previous_dates = sorted(k for k in series if k < key)
                if previous_dates:
                    row[name + '_previous'] = series[previous_dates[-1]]
        missing = [f for f in ('nasdaq', 'dow') if row.get(f) is None]
        row['status'] = 'Complete' if not missing else 'Unavailable: ' + ', '.join(missing) + ' (holiday or close pending/error)'
        row['detail'] = ' | '.join(source_errors) if missing else ''
        if missing:
            errors.append('US ' + key + ': ' + row['status'])
    history['last_attempt_ist'] = stamp
    history['issues'] = errors
    return history

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=10)
    args = parser.parse_args()
    path = ROOT / 'history.json'
    history = json.loads(path.read_text()) if path.exists() else {'india': {}, 'us': {}}
    update(history, datetime.now(timezone.utc), days=args.days)
    path.write_text(json.dumps(history, indent=2, sort_keys=True) + '\n')
    print('Indian sessions:', len(history['india']), 'US sessions:', len(history['us']))
    print('\n'.join(history['issues']) or 'All requested closes available.')

if __name__ == '__main__':
    main()
