# Daily market close tracker

The current workbook is [Market_Close_Tracker.xlsx](Market_Close_Tracker.xlsx).
Open the file and choose **Download raw file** to download the latest Excel copy.
The cloud master updates automatically. A copy already downloaded to a computer
does not update itself. Store personal comments in a separate workbook because
the cloud workbook is rebuilt from the saved market history.

## Sheets

- **India:** Nifty 50 close and daily change, India VIX close and daily change,
  nearest options expiry, put and call OI, nearest-expiry PCR, and all-expiries PCR.
- **US:** Nasdaq **Composite** (not Nasdaq 100), Dow Jones Industrial Average,
  previous trading close, points and percentage changes. Dates are US session dates.

PCR = sum of reported NIFTY put OI / sum of reported NIFTY call OI across all
strikes in the stated expiry scope. Futures, BANKNIFTY and expired contracts are
excluded. OI retains the quantities in NSE's `OpnIntrst` field, in underlying
units, without conversion into lots. All-expiries PCR is therefore weighted by
reported underlying OI, which can differ from a ratio calculated in contracts
during lot-size transitions. On an expiry day, the nearest scope includes that
day's expiry if the final bhavcopy contains it. No trading signals are inferred.

## Schedule (IST)

- 6:15 PM: Indian close update attempt.
- 9:15 PM: retry after final reports have had more time to publish.
- 6:15 AM: US close update attempt.
- 8:15 AM: retry for delayed publications.

Every run checks both sheets and retries missing data in the last 10 calendar
days. GitHub schedules can be delayed and are not an exact-time service. Standard
weekday sessions are tracked. Exchange holidays without reports are shown as
unavailable, never as zero or a copied previous close. Special weekend trading
sessions are not currently included. For a longer recovery/backfill, run
`python market-tracker/collect.py --days 60` and then the workbook filler.

## Sources and checks

- India: official [NSE daily index snapshots](https://www.nseindia.com/all-reports)
  and [final F&O UDiFF bhavcopies](https://www.nseindia.com/all-reports-derivatives).
  The parser verifies the report's session date, required indices, unique
  contract IDs, and valid OI. Index changes use NSE's published prior-session
  comparison rather than treating the previous calendar day as a trading day.
- US: Yahoo Finance dated daily bars for `^IXIC` and `^DJI`, admitted only after
  4:20 PM New York time. [FRED NASDAQCOM](https://fred.stlouisfed.org/series/NASDAQCOM)
  and [FRED DJIA](https://fred.stlouisfed.org/series/DJIA) are fallback sources;
  their publication can lag the market close. Each value's actual source is saved.

Missing values remain blank with a reason in Data status / Fetch detail.
Existing verified values survive a failed refresh. `history.json` is the
authoritative history, keyed by market and session date to prevent duplicate rows.
US comparison closes come from the previous available dated observation in the
same source. The Excel ratios and changes are formulas, with calculation caches
also supplied for viewers. Dates and market values are numeric Excel cells.

## Operation

The separate `market-close-tracker.yml` workflow uses Python 3.12's standard
library and a pre-authored Excel template. No pip installs, paid data keys,
broker login, or trading permissions are needed. There are no broker endpoints.
It commits the latest history and workbook to this repository and uploads a
downloadable workbook artifact on each successful run. Existing bot files and
Telegram workflows are independent.

To run manually: repository **Actions → Market close Excel tracker → Run workflow**.
Inspect the run's **Summary** for pending data. The workflow cannot guarantee
source availability. Its status must be checked if the file stops updating.
The template has space for 2,600 records per sheet (about ten trading years).
Exceeding that capacity raises an error instead of truncating history.

Local checks: `python -m unittest discover -s market-tracker -p 'test_*.py'`.
Local refresh: `python market-tracker/collect.py` followed by
`python market-tracker/fill_workbook.py`.
