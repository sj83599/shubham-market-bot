import csv
import io
import unittest
from datetime import date, datetime, timezone
from zipfile import ZipFile
from collect import index_rows, option_rows, yahoo_rows

class DataTests(unittest.TestCase):
    def test_exact_session_and_missing_index(self):
        payload = b'Index Name,Index Date,Closing Index Value,Points Change,Change(%)\nNifty 50,13-11-2026,25000,100,0.4\nIndia VIX,13-11-2026,15,-1,-6.25\n'
        self.assertEqual(index_rows(payload, date(2026,11,13))['vix'], 15)
        with self.assertRaises(ValueError):
            index_rows(payload, date(2026,11,12))
        with self.assertRaises(ValueError):
            index_rows(payload.split(b'India VIX')[0], date(2026,11,13))

    def test_expiry_scope_and_zero_call(self):
        def payload(call):
            stream = io.BytesIO()
            with ZipFile(stream,'w') as archive:
                archive.writestr('data.csv', 'TradDt,TckrSymb,OptnTp,XpryDt,OpnIntrst,FinInstrmId\n'
                    f'2026-11-13,NIFTY,CE,2026-11-17,{call},1\n'
                    '2026-11-13,NIFTY,PE,2026-11-17,200,2\n'
                    '2026-11-13,NIFTY,CE,2026-12-01,300,3\n'
                    '2026-11-13,NIFTY,PE,2026-12-01,100,4\n'
                    '2026-11-13,NIFTY,PE,2026-11-10,9999,5\n'
                    '2026-11-13,BANKNIFTY,PE,2026-11-17,9999,6\n')
            return stream.getvalue()
        r=option_rows(payload(100),date(2026,11,13))
        self.assertEqual(r['near_put']/r['near_call'],2)
        self.assertEqual(r['all_put']/r['all_call'],0.75)
        with self.assertRaises(ValueError):
            option_rows(payload(0),date(2026,11,13))

    def test_reject_intraday_us_bar(self):
        import json
        stamp=int(datetime(2026,11,13,14,30,tzinfo=timezone.utc).timestamp())
        payload=json.dumps({'chart':{'result':[{'meta':{'symbol':'^IXIC'},'timestamp':[stamp],
                  'indicators':{'quote':[{'close':[25000]}]}}], 'error':None}}).encode()
        self.assertEqual(yahoo_rows(payload,'^IXIC',datetime(2026,11,13,20,0,tzinfo=timezone.utc)),{})
        self.assertEqual(yahoo_rows(payload,'^IXIC',datetime(2026,11,13,22,0,tzinfo=timezone.utc)),{'2026-11-13':25000})

if __name__=='__main__':
    unittest.main()
