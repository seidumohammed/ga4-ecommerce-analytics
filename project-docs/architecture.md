# Architecture and design decisions

## The layers

| Layer | Schema | Purpose | Rule |
|---|---|---|---|
| Bronze | `bronze` | Raw copies of what was received, plus the source file and load time | Never cleaned. Anything wrong in the source stays visible here. |
| Silver | `silver` | Typed, flattened, deduplicated and conformed data at event, session, purchase, item and product grain | Fix what can be fixed from the data alone. Flag what cannot. Never delete without counting. |
| Gold | `gold` | Tables built for a question: daily KPIs, channel economics, funnel, products, cohorts, data quality | One definition per metric, tested to reconcile with the others. |

Each model lives in its own file under `models/bronze`, `models/silver` or `models/gold`, with a description and tests in the
yml file beside it. dbt builds the models in dependency order, so the lineage graph in `docs/lineage` is always the real one.

## Lineage

```
bronze_ga4_events --> silver_ga4_events --+--> silver_ga4_sessions --+--> mart_traffic_daily
                                          |                          +--> mart_funnel
                                          |                          +--> mart_cohort_retention
                                          |                          +--> mart_channel_performance <-- silver_marketing_spend
                                          |                          +--> mart_daily_kpis
                                          +--> silver_ga4_purchases --+--> silver_ga4_purchase_items --> mart_product_performance
                                          +--> silver_ga4_item_events ------------------------------------^
bronze_marketing_spend --> silver_marketing_spend --> mart_ad_spend_daily
bronze_product_catalog --> silver_products -----------> mart_product_performance
```

Open `docs/lineage/index.html` for the interactive graph, column descriptions and the compiled SQL of every model.

## Decisions and why

**Bronze keeps everything.** If a number is questioned later, the raw row is still there. Bronze models read the files
directly and add only the file name and load time.

**Flatten once, in silver.** GA4 stores most fields inside a list of key and value pairs (`event_params`). The macro
`ga4_param` reads one key from that list, and `silver_ga4_events` is the only model that does it. Everything after silver
uses ordinary columns.

**Deduplicate on an event key.** Each event gets a hash of the user, the timestamp, the event name, the session, the
transaction and the page. Rows with the same key are copies, and the first one is kept. The number removed is reported.

**Flag late events, do not drop them.** An event written to a later day's file than its own date is still a real event.
It is kept and flagged, and the daily tables use the event's own date.

**Sessions follow GA4.** A session is a user plus `ga_session_id`. Source, medium and campaign come from the first events
of the session. A session is engaged after 10 seconds of engagement, 2 page views or a purchase. Thresholds for bots and
engagement are variables in `dbt_project.yml`, so they can be changed in one place and are covered by unit tests.

**Bots and internal traffic are flagged in silver and excluded in gold.** The flag lives on the session. Every gold table
uses `is_valid_traffic`, so no mart can forget the rule. `mart_traffic_daily` shows the same numbers the dashboard uses.

**One purchase per transaction.** The purchase tag fires twice for some orders. Purchases are deduplicated on
`transaction_id`, and the number of extra firings is kept in `events_for_transaction`.

**The funnel counts "reached this step or later".** Tracking events get lost. If a session has an add-to-cart event but its
view-item event is missing, it still counts as having viewed a product. This keeps the funnel from growing at any step, and a
test checks that.

**Normalisation.** Product facts (name, category, cost) live once in `silver_products`. Purchases and their items are
separate tables joined on `transaction_id`. Facts at session, purchase and item grain share keys, so marts join cleanly.

**Two ways to date an order, both documented.** `mart_daily_kpis` dates a purchase when it happened, as GA4 does.
`mart_traffic_daily` and `mart_channel_performance` date it by the session start, so revenue can be split by channel and
device. They differ only for sessions that cross midnight, and a test proves that is the only cause.

**Attribution is the session's own source.** Revenue is credited to the channel of the session that bought. That is simple and
easy to audit, but it is not multi-touch attribution. Purchases with no session id are counted as unattributed instead of
being guessed.

## Tests

| Kind | What it protects |
|---|---|
| Generic data tests | Keys are unique and not empty, values are in the allowed list, joins find their parent rows. |
| Reconciliation tests (SQL) | Money and counts agree across layers and marts. |
| Unit tests | Business rules (bots, engagement, channel group, deduplication) on small hand-written inputs. |
| Planted-problem tests (pytest) | The pipeline finds exactly the problems the generator planted. |

A test suite that has never failed proves little. During development these tests caught a real definition difference
(order dates around midnight), a real flaw (spend counted by whole weeks against revenue by day), and a bug in the generator.
I also broke two rules on purpose and confirmed the matching tests failed.

## Known limits

- DuckDB is the engine so that the project runs anywhere with no cloud account. The SQL uses DuckDB features (lambda
  functions on lists, `arg_min`, `QUALIFY`). [run-on-real-ga4.md](run-on-real-ga4.md) lists what changes on BigQuery.
- The pipeline rebuilds every table on each run. That is fine for 745,000 events. A real shop would load new days
  incrementally and keep bronze append-only.
- Sessions with no user id cannot be separated when they start in the same second, so a few merge.
- The product funnel is item-level and approximate. The session funnel is exact.
