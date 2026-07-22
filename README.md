# Irish Residential Property Price Analysis

Analysis of every residential property sale registered in Ireland since 2010, using the
official **Property Price Register** — with a goal of understanding what drives price
differences across counties and building a simple, honest predictive model.

**Status: in progress (Day 1/2 — data cleaning + database load done, SQL/model/dashboard next).**

## Data source

[Property Price Register](https://www.propertypriceregister.ie/) — Ireland's official
register of residential property sales, published by the Property Services Regulatory
Authority. Free, no login, full history CSV download. ~795,000 rows (2010–present).

The raw file is **not committed to this repo** (108MB, over GitHub's comfortable limits).
To reproduce: download the full CSV from the link above and place it at
`data/raw/PPR-ALL.csv`.

## What's in this repo

| Path | Contents |
|---|---|
| `notebook/clean_data.py` | Cleans the raw PPR export into an analysis-ready dataset |
| `data/clean/properties_sample.csv` | 10,000-row random sample of the cleaned data (committed, for quick inspection) |
| `data/clean/county_year_summary.csv` | Median/mean price and sale count by county and year (committed) |
| `data/clean/properties_clean.csv` | Full cleaned dataset, ~795k rows (gitignored — regenerate locally) |
| `sql/` | SQL analysis queries (coming next) |
| `dashboard/` | Power BI dashboard screenshots (coming next) |

## Cleaning steps (`notebook/clean_data.py`)

- Parsed dates (`dd/mm/yyyy`) and derived year/quarter
- Stripped the currency symbol and thousands separators from price, cast to float
- Normalized county names (casing/whitespace)
- Validated Eircodes with a regex — invalid/blank values are set to null rather than kept as garbage strings
- Converted `Not Full Market Price` and `VAT Exclusive` from Yes/No text to booleans
- **Flagged** (not silently deleted) 27,411 statistical outliers using an IQR rule on log-transformed price, and 40,518 sales marked "Not Full Market Price" — both are kept in the dataset with a boolean flag so downstream analysis can choose to include or exclude them
- Added a log-price column (raw price is heavily right-skewed)

Raw rows: 795,347 → Rows remaining after dropping unusable records (missing price/date): 795,347 (none dropped in this run).

## Reproduce locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install pandas numpy
python notebook/clean_data.py
```

## Known limitations

- Price is the *registered sale price* — it doesn't capture property size/condition/BER directly, so any model built on this data alone has real limits (noted again wherever a model is presented).
- "Not Full Market Price" sales (e.g. transfers between relatives) are flagged, not excluded by default — worth testing sensitivity to this choice.
- Eircode coverage in the source data is sparse; county-level analysis is more reliable than Eircode-level.

## Next steps

- [ ] Load cleaned data into Postgres
- [ ] SQL analysis: YoY price change by county, rolling median, county growth ranking
- [ ] scikit-learn regression: predict price band from county, property type, year (report R² and top features honestly)
- [ ] Power BI dashboard: choropleth map of Ireland by median price, trend view, drill-through by county
- [ ] LinkedIn write-up
