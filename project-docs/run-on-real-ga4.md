# Running the pipeline on a real GA4 export

**Status: not yet run.** The project was built and tested on synthetic data. The generator reproduces the layout of the GA4
BigQuery export, but nothing here has been run against a real export, so expect to fix small things. This guide lists what
to check.

## The free sample

Google publishes a sample GA4 export for its merchandise web shop as a public BigQuery dataset,
`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*` (1 November 2020 to 31 January 2021). Reading it needs a
Google Cloud project with the BigQuery API turned on. The BigQuery sandbox is free. Some values in the sample are replaced
with placeholders such as `<Other>`.

## Option A: export a slice to Parquet and keep DuckDB (closest to this project)

1. In BigQuery, run `EXPORT DATA` to write a few weeks of `events_*` to a Cloud Storage bucket as Parquet, then download the files.
   The Parquet files keep the nested `event_params`, `items`, `device` and `geo` structures.
2. Rename the files `events_YYYYMMDD.parquet` into a folder `ga4/` under a raw folder of your choice.
3. Set `GA4_RAW_PATH` to that raw folder, set `GA4_DB_PATH`, and run `dbt build --profiles-dir .`.
4. Remove the secondary sources or replace them with your own `marketing_spend.csv` and `product_catalog.csv` in
   `secondary/`. The sample has no ad spend, so `mart_channel_performance` will show no spend.

Things to check, because the real export differs from the synthetic one:

| Area | What to check |
|---|---|
| Columns | The real export has more columns. `union_by_name = true` handles extras, but the silver models read only the columns they need. |
| Transaction id | Some purchase events carry the id in `ecommerce.transaction_id` and not in `event_params`. If `silver_ga4_purchases` is empty, read it with `coalesce(<param>, ecommerce.transaction_id)`. |
| Parameter types | A value such as `value` can arrive in `int_value`, `float_value` or `double_value`. `ga4_param` reads one type, so extend it with `coalesce` across the types. |
| Traffic source | Newer exports carry `collected_traffic_source`, and session source can also come from `session_traffic_source_last_click`. Compare them with the source in `session_start`. |
| Placeholders | Replace `<Other>`, `NULL` and empty strings with real NULLs in silver, as is already done for `(not set)`. |
| Late events | The real export has daily tables and a streaming table. The "late event" rule assumes the file date is the arrival date. |
| Internal traffic | The synthetic data marks internal traffic with the `traffic_type` parameter. A real property may use another setting. |
| Test expectations | The planted-problem tests compare against the generator's manifest and will not apply. The dbt tests still do. |

## Option B: run the models on BigQuery with dbt-bigquery

The SQL uses DuckDB features, so the models need changes:

| DuckDB (this project) | BigQuery |
|---|---|
| `list_filter(event_params, lambda p: ...)[1].value.string_value` | `(SELECT value.string_value FROM UNNEST(event_params) WHERE key = '...')` |
| `make_timestamp(event_timestamp)` | `TIMESTAMP_MICROS(event_timestamp)` |
| `strptime(event_date, '%Y%m%d')::date` | `PARSE_DATE('%Y%m%d', event_date)` |
| `arg_min(x, ts) filter (where ...)` | `ARRAY_AGG(x IGNORE NULLS ORDER BY ts LIMIT 1)[OFFSET(0)]` |
| `count(*) filter (where ...)` | `COUNTIF(...)` |
| `generate_series(a, b, interval 1 day)` | `GENERATE_DATE_ARRAY(a, b)` |
| `read_parquet(...)` in bronze | A `source()` on the export tables, or an external table |

Put the two engines behind small macros (`ga4_param` is the first) so only the macros change. Keep the tests: they are
plain SQL and most will run unchanged.

## When it runs

Compare the daily sessions, purchases and revenue with the GA4 interface for the same dates. Small differences are normal
(GA4 applies its own thresholds and modelling). Large ones point to a parameter that was read from the wrong place.
