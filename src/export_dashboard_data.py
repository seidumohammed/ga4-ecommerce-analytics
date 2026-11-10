"""Export the gold tables to small JSON files for the dashboard in docs/, and to CSV files for Power BI or Tableau.

    python src/export_dashboard_data.py            # reads GA4_DB_PATH, writes docs/data/*.json and exports/*.csv
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = os.environ.get("GA4_DB_PATH", str(ROOT / "data" / "warehouse" / "ga4.duckdb"))

# table -> columns the dashboard needs (JSON); every gold table is also written to CSV
DASHBOARD = {
    "daily_kpis": "select date_day, week_start, sessions, users, engaged_sessions, purchasing_sessions, purchases, revenue, "
                  "unattributed_revenue, bot_sessions_excluded, internal_sessions_excluded from gold.mart_daily_kpis order by date_day",
    "traffic_daily": "select date_day, channel_group, device_category, sessions, engaged_sessions, purchasing_sessions, purchases, revenue "
                     "from gold.mart_traffic_daily order by date_day, channel_group, device_category",
    "funnel_daily": "select session_date as date_day, device_category, channel_group, sessions, product_view_sessions, add_to_cart_sessions, "
                    "begin_checkout_sessions, shipping_info_sessions, payment_info_sessions, purchase_sessions from gold.mart_funnel order by 1, 2, 3",
    "spend_daily": "select date_day, channel_group, campaign, spend, clicks, impressions from gold.mart_ad_spend_daily order by date_day, channel_group, campaign",
    "products": "select item_id, item_name, category, list_price, unit_cost, product_views, add_to_cart_events, orders, units_sold, revenue, "
                "gross_margin, gross_margin_rate from gold.mart_product_performance order by revenue desc",
    "retention": "select cohort_week, weeks_since_first_visit, cohort_size, active_users, retention_rate from gold.mart_cohort_retention "
                 "order by cohort_week, weeks_since_first_visit",
    "data_quality": "select check_name, layer, rows_affected, description, handling from gold.mart_data_quality order by rows_affected desc",
}
GOLD_TABLES = ["dim_date", "mart_daily_kpis", "mart_traffic_daily", "mart_ad_spend_daily", "mart_channel_performance", "mart_funnel",
               "mart_product_performance", "mart_cohort_retention", "mart_data_quality"]


def rows(con, sql: str):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, [str(v) if hasattr(v, "isoformat") else v for v in r])) for r in cur.fetchall()]


def main() -> None:
    con = duckdb.connect(DB, read_only=True)
    out = ROOT / "docs" / "data"
    out.mkdir(parents=True, exist_ok=True)
    for name, sql in DASHBOARD.items():
        data = rows(con, sql)
        (out / f"{name}.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(f"docs/data/{name}.json  {len(data):>6} rows")
    exports = ROOT / "exports"
    exports.mkdir(exist_ok=True)
    for t in GOLD_TABLES:
        path = (exports / f"{t}.csv").as_posix()
        con.execute(f"copy (select * from gold.{t}) to '{path}' (header, delimiter ',')")
    print(f"exports/*.csv  {len(GOLD_TABLES)} files for Power BI or Tableau")


if __name__ == "__main__":
    main()
