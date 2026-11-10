import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from ga4_synth.generate import SCHEMA, main  # noqa: E402


@pytest.fixture(scope="module")
def small_export(tmp_path_factory):
    out = tmp_path_factory.mktemp("ga4")
    manifest = main(str(out), seed=7, sessions_per_day=150, days=4)
    return out, manifest


def read_all(out: Path):
    return [pq.read_table(f) for f in sorted((out / "ga4").glob("events_*.parquet"))]


def test_files_follow_the_daily_export_layout(small_export):
    out, _ = small_export
    names = [f.name for f in sorted((out / "ga4").glob("events_*.parquet"))]
    assert names[:4] == [f"events_2025100{d}.parquet" for d in (1, 2, 3, 4)]
    for t in read_all(out):
        assert t.schema.names == SCHEMA.names


def test_same_seed_gives_the_same_data(small_export, tmp_path):
    _, first = small_export
    again = main(str(tmp_path), seed=7, sessions_per_day=150, days=4)
    assert again == first


def test_a_different_seed_gives_different_data(small_export, tmp_path):
    _, first = small_export
    other = main(str(tmp_path), seed=8, sessions_per_day=150, days=4)
    assert other["events"] != first["events"]


def test_planted_problems_are_present(small_export):
    _, m = small_export
    for key in ("duplicate_rows", "late_rows", "events_without_session_id", "bot_sessions", "consent_denied_sessions"):
        assert m[key] > 0, key
    assert m["spend_negative_adjustments"] == 1 and m["catalog_duplicate_rows"] == 1


def test_manifest_matches_the_files(small_export):
    out, m = small_export
    rows = sum(t.num_rows for t in read_all(out))
    # the last file also holds late events carried past the final day, which the manifest does not count
    assert rows >= m["events"]


def test_purchases_are_internally_consistent(small_export):
    out, _ = small_export
    checked = 0
    for t in read_all(out):
        for r in t.to_pylist():
            if r["event_name"] != "purchase":
                continue
            params = {p["key"]: p["value"] for p in r["event_params"]}
            e = r["ecommerce"]
            assert params["transaction_id"]["string_value"] == e["transaction_id"]
            assert params["value"]["double_value"] == pytest.approx(e["purchase_revenue"])
            items_total = sum(i["item_revenue"] for i in r["items"])
            assert items_total + e["shipping_value_in_usd"] == pytest.approx(e["purchase_revenue"], abs=0.011)
            checked += 1
    assert checked > 0


def test_secondary_sources_are_written(small_export):
    out, _ = small_export
    spend = (out / "secondary" / "marketing_spend.csv").read_text(encoding="utf-8").splitlines()
    assert spend[0] == "date,platform,campaign_name,clicks,impressions,cost,currency"
    assert any(",-35.0," in line for line in spend)
    catalog = (out / "secondary" / "product_catalog.csv").read_text(encoding="utf-8").splitlines()
    assert len(catalog) == 1 + 30 + 1  # header, 30 products, 1 repeated row
    assert json.loads((out / "generation_manifest.json").read_text(encoding="utf-8"))["seed"] == 7
