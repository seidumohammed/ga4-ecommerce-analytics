# GA4 E-commerce Analytics Platform

A bronze, silver and gold analytics pipeline for the web data of an online shop, built with SQL, dbt and DuckDB. It
turns raw GA4-style event files and two secondary sources (ad spend and a product catalogue) into tested tables for
the questions a marketing and e-commerce team asks, and puts them in a dashboard.

**All data is synthetic.** The shop, its customers and its numbers are invented. The event files follow the layout of
the GA4 BigQuery export, and known data problems are planted on purpose so the pipeline can be tested against a known
answer. The project has not been run on a real GA4 export yet. [project-docs/run-on-real-ga4.md](project-docs/run-on-real-ga4.md)
explains how to do that.

- **Dashboard:** https://seidumohammed.github.io/ga4-ecommerce-analytics/
- **Lineage graph and model documentation:** https://seidumohammed.github.io/ga4-ecommerce-analytics/lineage/

## What it covers

| Skill | Where to look |
|---|---|
| Collect, clean and validate data from primary and secondary sources | GA4 event files (primary), ad spend and product catalogue (secondary). 12 kinds of data problem are found, fixed and counted in `gold.mart_data_quality`. |
| SQL to extract and transform data | 19 dbt models in `models/`: window functions, `QUALIFY`, nested `UNNEST`, filtered aggregates, sessionisation. |
| Dashboards | `docs/index.html` (filters, KPI cards, funnel, channel return on ad spend, cohorts). `exports/` holds CSV files for Power BI or Tableau. |
| GA4 | The export layout (`event_params`, `items`, `device`, `geo`, traffic fields), sessions from `ga_session_id`, the engagement rule, the default channel group, e-commerce events. |
| Data models, medallion architecture, lineage | Bronze, silver and gold schemas, a lineage graph from `dbt docs`, and the design choices in [project-docs/architecture.md](project-docs/architecture.md). |
| AI-assisted delivery | [project-docs/ai-assisted-delivery.md](project-docs/ai-assisted-delivery.md): how AI help was used here, and the checks that keep it honest. |
| Leading a small analytics project | [project-docs/business-brief.md](project-docs/business-brief.md): the questions, metric definitions, findings and recommended actions. |

## How it fits together

```
 GA4-style event files (daily parquet)        Ad spend (csv)       Product catalogue (csv)
            |                                       |                       |
            +-------------------+-------------------+-----------------------+
                                v
   BRONZE  raw copies, nothing cleaned            bronze_ga4_events, bronze_marketing_spend, bronze_product_catalog
                                v
   SILVER  typed, flattened, deduplicated,        silver_ga4_events -> silver_ga4_sessions, silver_ga4_purchases,
           sessionised, conformed                 silver_ga4_purchase_items, silver_ga4_item_events,
                                                  silver_marketing_spend, silver_products
                                v
   GOLD    tables built for questions             mart_daily_kpis, mart_traffic_daily, mart_channel_performance,
                                                  mart_ad_spend_daily, mart_funnel, mart_product_performance,
                                                  mart_cohort_retention, mart_data_quality, dim_date
                                v
           Dashboard (docs/index.html), CSV exports, lineage graph
```

## What the pipeline found in the raw data

The generator plants these problems and records how many it planted. The pipeline finds them from the data alone, and
a test checks that every count matches.

| Problem | Rows | Handling |
|---|---|---|
| Exact duplicate event rows | 6,053 | Removed, first copy kept |
| Events written to a later day's file than their own date | 11,278 | Kept and flagged |
| Events with no session id | 3,801 | Kept in event tables, left out of sessions |
| Sessions with no user id (consent refused) | 3,075 | Kept for traffic, left out of user counts and cohorts |
| Bot sessions | 1,217 | Flagged and excluded from the marts |
| Internal and test sessions | 575 | Flagged and excluded from the marts |
| Purchase tag fired twice for one order | 27 | One purchase per transaction id |
| Currency code sent in lower case | 30 | Upper-cased |
| Campaign names spelt differently in the ad platform | 74 | Standardised to match GA4 |
| Repeated product in the catalogue | 1 | Removed |
| Negative cost row (billing adjustment) | 1 | Kept and flagged |
| Days with no Paid Social spend rows | 2 | Reported |

The effect on the numbers: the raw files hold 2,635 purchase rows and $169,967 of revenue. After cleaning there are
2,578 orders from real customers (2,592 including 14 internal test orders) and $166,094 of revenue, so using the raw rows
would overstate revenue by 2.3%. Of the 101,947 sessions, 100,155 are human and external.

## How it is tested

`dbt build` runs 19 models, 45 data tests and 5 unit tests, and `pytest` runs 22 more tests.

- **Data tests (45):** unique and not-null keys, accepted values, relationships, and seven reconciliation tests written in
  SQL. They check that order revenue minus shipping equals item revenue, that channel revenue plus unattributed revenue
  equals the daily total, that the traffic and daily tables agree, that the two ad spend tables agree with the source, that
  the funnel never grows, that every rate is between 0 and 1, and that no event is lost between layers.
- **Unit tests (5):** bot detection, the GA4 engagement rule, channel grouping and purchase deduplication, each on small
  hand-written inputs.
- **Planted-problem tests (pytest):** the pipeline's findings must equal the generator's manifest. This caught a bug in the
  generator itself during development.
- **Break tests:** I changed two rules on purpose (email traffic labelled as referral, item revenue inflated by 1%) and
  confirmed the tests failed.

## Run it

You need Python 3.12 or newer.

```bash
python -m venv .venv
.venv/Scripts/activate            # on macOS or Linux: source .venv/bin/activate
pip install -r requirements.txt

# 1. generate the synthetic data (about 2 minutes for the full 92 days)
cd src && python -m ga4_synth.generate --out ../data/raw && cd ..

# 2. build and test everything (bronze, silver, gold)
dbt build --profiles-dir .

# 3. check the pipeline found the planted problems
pytest

# 4. refresh the dashboard data and the lineage graph
python src/export_dashboard_data.py
dbt docs generate --static --profiles-dir . && cp target/static_index.html docs/lineage/index.html
```

Use `--days 30 --sessions-per-day 300` in step 1 for a quick run. To keep large files outside a synced folder, set
`GA4_RAW_PATH` and `GA4_DB_PATH` before running dbt and pytest. Open `docs/index.html` through any local web server, for
example `python -m http.server --directory docs`.

## Layout

```
src/ga4_synth/generate.py     synthetic GA4-style export, secondary sources and a manifest of planted problems
src/export_dashboard_data.py  gold tables to JSON (dashboard) and CSV (Power BI, Tableau)
models/bronze|silver|gold     the dbt models, with descriptions and tests in the yml files
macros/                       ga4_param (read an event parameter), channel_group (default channel group)
dbt_tests/                    reconciliation tests written in SQL
tests/                        pytest: the generator, and the pipeline against the planted problems
docs/                         dashboard (index.html), its data, and the lineage graph
project-docs/                 business brief, architecture, AI-assisted delivery, real GA4 guide
```

## Limits

- The data is synthetic. Patterns such as the Black Friday peak and the mobile conversion gap were built into the
  generator, so the findings show what the pipeline can surface, not what a real shop would find.
- Sessions with no user id cannot be told apart if they start in the same second. In this data 1 such session was
  merged out of 3,076.
- Revenue is credited to the session that bought, using the session's own source (last click inside the session). It is
  not multi-touch attribution. Purchases with no session id cannot be credited to a channel and are shown as unattributed.
- The channel grouping is a simplified version of the GA4 default channel group.
- Orders are dated by purchase time in `mart_daily_kpis` and by session start in the traffic and channel tables, so the
  two differ on days when a session crosses midnight. Totals over the whole period are identical.
- Ad spend is not split by device, so return on ad spend is shown only when all devices are selected.
