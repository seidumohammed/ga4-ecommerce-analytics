"""Check that the pipeline found the problems the generator planted. Runs after `dbt build`; skipped if there is no warehouse.

Set GA4_DB_PATH and GA4_RAW_PATH to the same values used for dbt.
"""

import json
import os
from pathlib import Path

import duckdb
import pytest

DB = os.environ.get("GA4_DB_PATH", "data/warehouse/ga4.duckdb")
RAW = os.environ.get("GA4_RAW_PATH", "data/raw")
ready = Path(DB).exists() and (Path(RAW) / "generation_manifest.json").exists()
pytestmark = pytest.mark.skipif(not ready, reason="run the generator and `dbt build` first")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(DB, read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def planted():
    return json.loads((Path(RAW) / "generation_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def found(con):
    return dict(con.sql("select check_name, rows_affected from gold.mart_data_quality").fetchall())


# manifest key -> data-quality check name. Each must match exactly.
EXACT = {
    "duplicate_rows": "duplicate_event_rows",
    "late_rows": "late_arriving_event_rows",
    "events_without_session_id": "events_without_session_id",
    "bot_sessions": "bot_sessions",
    "internal_sessions": "internal_sessions",
    "double_purchase_events": "double_fired_purchase_events",
    "lowercase_currency_purchases": "lowercase_currency_purchases",
    "catalog_duplicate_rows": "catalog_duplicate_rows",
    "spend_campaign_name_variants": "spend_campaign_name_variants",
    "spend_negative_adjustments": "spend_negative_adjustments",
    "spend_days_missing_for_meta": "paid_social_days_without_spend",
}


@pytest.mark.parametrize("planted_key,check", EXACT.items())
def test_every_planted_problem_is_found_exactly(planted, found, planted_key, check):
    assert found[check] == planted[planted_key], f"{check}: found {found[check]}, planted {planted[planted_key]}"


def test_consent_denied_sessions_are_found_within_collisions(planted, found):
    """Sessions with no user id cannot be told apart if they start in the same second, so a few can merge."""
    assert planted["consent_denied_sessions"] - 0.01 * planted["consent_denied_sessions"] <= found["consent_denied_sessions"] \
        <= planted["consent_denied_sessions"]


def test_sessions_match_generated_sessions(con, planted):
    n = con.sql("select count(*) from silver.silver_ga4_sessions").fetchall()[0][0]
    assert planted["sessions"] * 0.995 <= n <= planted["sessions"]


def test_all_real_orders_survive_cleaning(con, planted):
    n = con.sql("select count(*) from silver.silver_ga4_purchases").fetchall()[0][0]
    assert n == planted["purchases"]


def test_internal_test_orders_are_kept_out_of_revenue(con, planted):
    orders = con.sql("select sum(purchases) from gold.mart_daily_kpis").fetchall()[0][0]
    assert orders == planted["purchases"] - planted["internal_purchases"]
