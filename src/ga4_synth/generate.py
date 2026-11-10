"""Synthetic GA4 BigQuery-export-style data for a fictional online shop.

ALL DATA IS SYNTHETIC. The shop, its customers, products and numbers are invented. The event files follow the
layout of the GA4 BigQuery export (one table per day, nested event_params, items, device, geo and traffic fields,
a subset of the real columns) so that the pipeline can be pointed at a real export later.

Known data problems are planted on purpose, and their counts are written to a manifest so tests can check that
the pipeline finds every one of them.

    python -m ga4_synth.generate --out data/raw
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

START = date(2025, 10, 1)
DAYS = 92  # 2025-10-01 to 2025-12-31
HOST = "shop.example.com"
STREAM_ID = "1000000001"
CURRENCY = "USD"

# ---------------------------------------------------------------- reference data
PRODUCTS = [  # item_id, name, category, brand, price, unit cost share of price
    ("APP-001", "Classic Cotton T-Shirt", "Apparel", "Kente Works", 18.0, 0.45),
    ("APP-002", "Heavy Hoodie", "Apparel", "Kente Works", 46.0, 0.50),
    ("APP-003", "Embroidered Cap", "Apparel", "Kente Works", 14.0, 0.42),
    ("APP-004", "Wool Scarf", "Apparel", "Harmattan", 24.0, 0.48),
    ("APP-005", "Rain Jacket", "Apparel", "Harmattan", 78.0, 0.55),
    ("APP-006", "Crew Socks 3-Pack", "Apparel", "Kente Works", 9.0, 0.40),
    ("DRK-001", "Steel Water Bottle", "Drinkware", "Sip", 22.0, 0.44),
    ("DRK-002", "Ceramic Mug", "Drinkware", "Sip", 12.0, 0.40),
    ("DRK-003", "Insulated Tumbler", "Drinkware", "Sip", 28.0, 0.46),
    ("DRK-004", "Travel Flask", "Drinkware", "Sip", 32.0, 0.47),
    ("DRK-005", "Cup Set of 4", "Drinkware", "Sip", 26.0, 0.50),
    ("BAG-001", "Everyday Backpack", "Bags", "Carry Co", 58.0, 0.52),
    ("BAG-002", "Canvas Tote", "Bags", "Carry Co", 16.0, 0.38),
    ("BAG-003", "Weekend Duffel", "Bags", "Carry Co", 72.0, 0.54),
    ("BAG-004", "Laptop Sleeve", "Bags", "Carry Co", 29.0, 0.45),
    ("BAG-005", "Zip Pouch", "Bags", "Carry Co", 8.0, 0.36),
    ("STA-001", "Hardcover Notebook", "Stationery", "Paperline", 11.0, 0.38),
    ("STA-002", "Pen Set", "Stationery", "Paperline", 15.0, 0.40),
    ("STA-003", "Sticker Pack", "Stationery", "Paperline", 5.0, 0.30),
    ("STA-004", "Weekly Planner", "Stationery", "Paperline", 19.0, 0.42),
    ("STA-005", "Large Desk Mat", "Stationery", "Paperline", 27.0, 0.46),
    ("TEC-001", "Phone Case", "Tech Accessories", "Volt", 17.0, 0.40),
    ("TEC-002", "Fast Charger", "Tech Accessories", "Volt", 25.0, 0.55),
    ("TEC-003", "Wireless Earbuds", "Tech Accessories", "Volt", 64.0, 0.60),
    ("TEC-004", "Cable Set", "Tech Accessories", "Volt", 13.0, 0.42),
    ("TEC-005", "Laptop Stand", "Tech Accessories", "Volt", 39.0, 0.50),
    ("HOM-001", "Scented Candle", "Home", "Hearth", 21.0, 0.40),
    ("HOM-002", "Throw Blanket", "Home", "Hearth", 44.0, 0.48),
    ("HOM-003", "Framed Wall Art", "Home", "Hearth", 55.0, 0.50),
    ("HOM-004", "Cushion Cover", "Home", "Hearth", 18.0, 0.40),
]
CATEGORY_SLUG = {c: c.lower().replace(" ", "-") for c in {p[2] for p in PRODUCTS}}

# channel: (source, medium, campaigns, weight, conversion multiplier)
CHANNELS = {
    "Direct": [("(direct)", "(none)", [None], 0.24, 1.15)],
    "Organic Search": [("google", "organic", [None], 0.22, 0.90), ("bing", "organic", [None], 0.05, 0.90)],
    "Paid Search": [("google", "cpc", ["brand_search", "generic_search", "bf_2025_search"], 0.14, 1.20)],
    "Paid Social": [("facebook", "paid_social", ["ugc_video", "retarget_cart", "bf_2025_social"], 0.07, 0.70),
                    ("instagram", "paid_social", ["ugc_video", "bf_2025_social"], 0.04, 0.70)],
    "Email": [("newsletter", "email", ["weekly_digest", "cart_recovery", "bf_2025_email"], 0.08, 1.90)],
    "Referral": [("blogger.example", "referral", [None], 0.05, 1.00)],
    "Organic Social": [("instagram", "social", [None], 0.05, 0.50)],
    "Display": [("google", "display", ["bf_2025_display", "remarketing"], 0.03, 0.35)],
    "Unassigned": [("(not set)", "(not set)", [None], 0.01, 0.60)],
}
PAID = {"Paid Search", "Paid Social", "Display", "Email"}
DEVICES = [("mobile", 0.62, 0.75), ("desktop", 0.33, 1.35), ("tablet", 0.05, 1.00)]
GEOS = [  # country, continent, region, cities, weight
    ("Ghana", "Africa", "Greater Accra", ["Accra", "Tema"], 0.24), ("Ghana", "Africa", "Ashanti", ["Kumasi"], 0.12),
    ("Nigeria", "Africa", "Lagos", ["Lagos"], 0.14), ("Nigeria", "Africa", "FCT", ["Abuja"], 0.08),
    ("Kenya", "Africa", "Nairobi", ["Nairobi"], 0.12),
    ("South Africa", "Africa", "Gauteng", ["Johannesburg"], 0.06), ("South Africa", "Africa", "Western Cape", ["Cape Town"], 0.04),
    ("United Kingdom", "Europe", "England", ["London", "Manchester"], 0.08),
    ("United States", "Americas", "New York", ["New York"], 0.04), ("United States", "Americas", "Texas", ["Austin"], 0.03),
    ("(not set)", "(not set)", "(not set)", ["(not set)"], 0.05),
]
MOBILE = [("Apple", "iPhone", "iOS"), ("Samsung", "Galaxy", "Android"), ("Tecno", "Spark", "Android"), ("Xiaomi", "Redmi", "Android")]
BROWSERS = {"mobile": ["Chrome", "Safari", "Samsung Internet"], "desktop": ["Chrome", "Edge", "Firefox", "Safari"], "tablet": ["Safari", "Chrome"]}
HOUR_W = [1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 8, 7, 6, 6, 6, 7, 8, 9, 9, 8, 5, 2]
WEEKDAY = [1.00, 0.98, 0.97, 1.00, 1.05, 1.12, 1.15]

# ---------------------------------------------------------------- planted problems (rates)
DUP_ROW_RATE = 0.008        # exact duplicate event rows
LATE_ROW_RATE = 0.015       # event written to the next day's file
NO_SESSION_ID_RATE = 0.005  # event without ga_session_id
CONSENT_DENIED_RATE = 0.03  # session without user_pseudo_id
BOT_RATE = 0.012            # non-human sessions
INTERNAL_RATE = 0.006       # internal / test traffic
DOUBLE_PURCHASE_RATE = 0.012
LOWERCASE_CURRENCY_RATE = 0.01

# ---------------------------------------------------------------- arrow schema (a subset of the GA4 export)
_val = pa.struct([("string_value", pa.string()), ("int_value", pa.int64()),
                  ("float_value", pa.float64()), ("double_value", pa.float64())])
_param = pa.struct([("key", pa.string()), ("value", _val)])
_item = pa.struct([("item_id", pa.string()), ("item_name", pa.string()), ("item_brand", pa.string()),
                   ("item_category", pa.string()), ("price_in_usd", pa.float64()), ("price", pa.float64()),
                   ("quantity", pa.int64()), ("item_revenue_in_usd", pa.float64()), ("item_revenue", pa.float64()),
                   ("item_list_name", pa.string()), ("item_list_index", pa.string())])
SCHEMA = pa.schema([
    ("event_date", pa.string()), ("event_timestamp", pa.int64()), ("event_name", pa.string()),
    ("event_params", pa.list_(_param)), ("event_value_in_usd", pa.float64()),
    ("user_id", pa.string()), ("user_pseudo_id", pa.string()),
    ("privacy_info", pa.struct([("analytics_storage", pa.string()), ("ads_storage", pa.string()),
                                ("uses_transient_token", pa.string())])),
    ("user_first_touch_timestamp", pa.int64()),
    ("user_ltv", pa.struct([("revenue", pa.float64()), ("currency", pa.string())])),
    ("device", pa.struct([("category", pa.string()), ("mobile_brand_name", pa.string()),
                          ("mobile_model_name", pa.string()), ("operating_system", pa.string()),
                          ("language", pa.string()),
                          ("web_info", pa.struct([("browser", pa.string()), ("hostname", pa.string())]))])),
    ("geo", pa.struct([("continent", pa.string()), ("country", pa.string()), ("region", pa.string()),
                       ("city", pa.string())])),
    ("traffic_source", pa.struct([("name", pa.string()), ("medium", pa.string()), ("source", pa.string())])),
    ("stream_id", pa.string()), ("platform", pa.string()),
    ("ecommerce", pa.struct([("total_item_quantity", pa.int64()), ("purchase_revenue_in_usd", pa.float64()),
                             ("purchase_revenue", pa.float64()), ("shipping_value_in_usd", pa.float64()),
                             ("unique_items", pa.int64()), ("transaction_id", pa.string())])),
    ("items", pa.list_(_item)),
    ("collected_traffic_source", pa.struct([("manual_campaign_name", pa.string()), ("manual_source", pa.string()),
                                            ("manual_medium", pa.string())])),
])


def P(key, s=None, i=None, d=None):
    return {"key": key, "value": {"string_value": s, "int_value": i, "float_value": None, "double_value": d}}


def pick(rng, rows, wi):
    """Weighted choice: rows is a list of tuples, wi the index of the weight."""
    x, acc = rng.random() * sum(r[wi] for r in rows), 0.0
    for r in rows:
        acc += r[wi]
        if x <= acc:
            return r
    return rows[-1]


def day_multiplier(d: date) -> float:
    m = WEEKDAY[d.weekday()] * (1 + 0.0025 * (d - START).days)
    if d == date(2025, 11, 28):
        m *= 2.4                           # Black Friday
    elif d == date(2025, 12, 1):
        m *= 1.8                           # Cyber Monday
    elif date(2025, 11, 24) <= d <= date(2025, 11, 30):
        m *= 1.3
    elif date(2025, 12, 15) <= d <= date(2025, 12, 23):
        m *= 1.35
    elif d in (date(2025, 12, 25), date(2025, 12, 26)):
        m *= 0.6
    return m


def campaign_boost(d: date, channel: str) -> float:
    in_bf = date(2025, 11, 24) <= d <= date(2025, 12, 1)
    return 1.6 if (in_bf and channel in PAID) else 1.0


def campaign_for(rng, pool, d: date):
    live = [c for c in pool if c is None or not c.startswith("bf_") or date(2025, 11, 20) <= d <= date(2025, 12, 3)]
    return rng.choice(live)


class Generator:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.users: list[str] = []
        self.user_state: dict[str, dict] = {}
        self.txn_counter = 100000
        self.m = dict(sessions=0, events=0, purchases=0, new_users=0, duplicate_rows=0, late_rows=0,
                      events_without_session_id=0, consent_denied_sessions=0, bot_sessions=0, internal_sessions=0,
                      double_purchase_events=0, lowercase_currency_purchases=0, internal_purchases=0)
        self.spend_clicks: dict[tuple, int] = {}   # (date, platform-channel, campaign) -> sessions
        self.session_rows: list[dict] = []

    # ------------------------------------------------------------- one session
    def session(self, d: date) -> list[dict]:
        r, m = self.rng, self.m
        ch_name = self._channel(d)
        src, med, camps, _, cvr_ch = pick(r, CHANNELS[ch_name], 3)
        campaign = campaign_for(r, camps, d)
        device, _, cvr_dev = pick(r, DEVICES, 1)
        geo = pick(r, GEOS, 4)
        city = r.choice(geo[3]) if r.random() > 0.08 else "(not set)"

        hour = r.choices(range(24), weights=HOUR_W)[0]
        t0 = datetime(d.year, d.month, d.day, hour, r.randrange(60), r.randrange(60), tzinfo=timezone.utc)
        ts = int(t0.timestamp() * 1_000_000)
        ga_session_id = int(t0.timestamp())

        is_bot = r.random() < BOT_RATE
        is_internal = (not is_bot) and r.random() < INTERNAL_RATE
        consent_denied = (not is_bot) and r.random() < CONSENT_DENIED_RATE
        if is_bot:
            src, med, campaign, ch_name = "(not set)", "(not set)", None, "Unassigned"
            m["bot_sessions"] += 1
        if is_internal:
            m["internal_sessions"] += 1
        if consent_denied:
            m["consent_denied_sessions"] += 1

        # user identity
        returning = (not is_bot) and self.users and r.random() < 0.32
        if returning:
            uid = r.choice(self.users)
            st = self.user_state[uid]
        else:
            uid = f"{r.randrange(10**8, 10**9)}.{ga_session_id}"
            st = dict(first_ts=ts, n=0, source=src, medium=med, name=campaign or "(direct)" if med == "(none)" else (campaign or "(organic)"),
                      ltv=0.0, lang="en-gb" if geo[0] in ("United Kingdom",) else "en-us")
            self.users.append(uid)
            self.user_state[uid] = st
            m["new_users"] += 1
        st["n"] += 1
        session_number = st["n"]

        mobile = r.choice(MOBILE) if device != "desktop" else (None, None, None)
        os_name = {"desktop": r.choice(["Windows", "Macintosh", "Linux"])}.get(device, mobile[2] or "Android")
        browser = "HeadlessChrome" if is_bot else r.choice(BROWSERS[device])
        user_pseudo_id = None if consent_denied else uid
        shared = dict(
            user_id=None, user_pseudo_id=user_pseudo_id,
            privacy_info={"analytics_storage": "No" if consent_denied else "Yes", "ads_storage": "Yes", "uses_transient_token": "No"},
            user_first_touch_timestamp=None if consent_denied else st["first_ts"],
            device={"category": device, "mobile_brand_name": mobile[0], "mobile_model_name": mobile[1],
                    "operating_system": os_name, "language": st["lang"], "web_info": {"browser": browser, "hostname": HOST}},
            geo={"continent": geo[1], "country": geo[0], "region": geo[2], "city": city},
            traffic_source={"name": st["name"], "medium": st["medium"], "source": st["source"]},
            stream_id=STREAM_ID, platform="WEB",
        )

        events: list[dict] = []
        clock = [ts]

        def emit(name, params, ecommerce=None, items=None, value=None, first=False):
            clock[0] += r.randrange(300_000, 25_000_000)
            base = [P("ga_session_id", i=ga_session_id), P("ga_session_number", i=session_number)]
            if first:
                base += [P("source", s=src), P("medium", s=med)] + ([P("campaign", s=campaign)] if campaign else [])
            if is_internal:
                base.append(P("traffic_type", s="internal"))
            ev = dict(shared, event_date=d.strftime("%Y%m%d"), event_timestamp=clock[0], event_name=name,
                      event_params=base + params, event_value_in_usd=value, ecommerce=ecommerce, items=items,
                      user_ltv=None, collected_traffic_source=(
                          {"manual_campaign_name": campaign, "manual_source": src, "manual_medium": med} if first else None))
            events.append(ev)

        def page(path, title, first=False):
            params = [P("page_location", s=f"https://{HOST}{path}"), P("page_title", s=title)]
            if first and src not in ("(direct)", "(not set)"):
                params.append(P("page_referrer", s=f"https://{src}/"))
            return params

        if is_bot:
            for _ in range(r.randrange(25, 90)):
                emit("page_view", page("/collections/" + r.choice(list(CATEGORY_SLUG.values())), "Collection"))
            return events

        if not returning:
            emit("first_visit", [], first=True)
        emit("session_start", [], first=True)

        viewed: list[tuple] = []
        n_pages = 1 + min(14, int(r.expovariate(1.15)))
        path_kind = r.choices(["home", "collection", "product", "blog"], weights=[0.30, 0.22, 0.38, 0.10])[0]
        eng_ms = 0
        for k in range(n_pages):
            if path_kind == "home" or (k == 0 and path_kind == "blog"):
                path, title = ("/", "Home") if path_kind == "home" else ("/blog/gift-guide", "Gift guide")
                emit("page_view", page(path, title, first=(k == 0)) + ([P("entrances", i=1)] if k == 0 else []))
            elif path_kind == "collection":
                prod = r.choice(PRODUCTS)
                cat = prod[2]
                emit("page_view", page(f"/collections/{CATEGORY_SLUG[cat]}", cat, first=(k == 0)) + ([P("entrances", i=1)] if k == 0 else []))
                emit("view_item_list", [P("item_list_name", s=f"{cat} collection")],
                     items=[self._item(p, 1, f"{cat} collection", j) for j, p in enumerate(r.sample(PRODUCTS, 3))])
            else:
                prod = r.choice(PRODUCTS)
                emit("page_view", page(f"/product/{prod[0].lower()}", prod[1], first=(k == 0)) + ([P("entrances", i=1)] if k == 0 else []))
                it = self._item(prod, 1, "Product page", 0)
                emit("view_item", [P("currency", s=CURRENCY), P("value", d=prod[4])], items=[it], value=prod[4])
                viewed.append(prod)
            if r.random() < 0.35:
                emit("scroll", [P("percent_scrolled", i=90)])
            ms = int(r.lognormvariate(8.6, 1.0))
            eng_ms += ms
            emit("user_engagement", [P("engagement_time_msec", i=ms)])
            path_kind = r.choices(["collection", "product", "home"], weights=[0.3, 0.55, 0.15])[0]

        # ---------------------------------------------------------------- the purchase funnel
        if not viewed and r.random() < 0.35:
            prod = r.choice(PRODUCTS); viewed.append(prod)
            emit("view_item", [P("currency", s=CURRENCY), P("value", d=prod[4])], items=[self._item(prod, 1, "Product page", 0)], value=prod[4])
        returning_boost = 1.25 if returning else 1.0
        cvr = cvr_ch * cvr_dev * returning_boost * campaign_boost(d, ch_name)
        converted = False
        if viewed and r.random() < min(0.45, 0.135 * cvr):
            cart = [(p, r.choice([1, 1, 1, 2])) for p in ([viewed[-1]] + r.sample(PRODUCTS, r.choice([0, 0, 1, 2])))]
            cart_items = [self._item(p, q, "Cart", j) for j, (p, q) in enumerate(cart)]
            subtotal = round(sum(p[4] * q for p, q in cart), 2)
            for p, q in cart[:1]:
                emit("add_to_cart", [P("currency", s=CURRENCY), P("value", d=p[4] * q)], items=[self._item(p, q, "Product page", 0)], value=p[4] * q)
            emit("view_cart", [P("currency", s=CURRENCY), P("value", d=subtotal)], items=cart_items, value=subtotal)
            if r.random() < 0.52:
                emit("begin_checkout", [P("currency", s=CURRENCY), P("value", d=subtotal)], items=cart_items, value=subtotal)
                if r.random() < 0.86:
                    emit("add_shipping_info", [P("currency", s=CURRENCY), P("value", d=subtotal), P("shipping_tier", s="Standard")], items=cart_items, value=subtotal)
                    if r.random() < 0.80:
                        emit("add_payment_info", [P("currency", s=CURRENCY), P("value", d=subtotal), P("payment_type", s=r.choice(["Card", "Mobile money", "Card"]))], items=cart_items, value=subtotal)
                        p_buy = 0.80 if device == "desktop" else (0.62 if device == "mobile" else 0.70)
                        if r.random() < p_buy:
                            converted = True
                            shipping = 0.0 if subtotal >= 50 else 4.5
                            total = round(subtotal + shipping, 2)
                            self.txn_counter += 1
                            txn = f"T-{self.txn_counter}"
                            currency = CURRENCY.lower() if r.random() < LOWERCASE_CURRENCY_RATE else CURRENCY
                            if currency != CURRENCY:
                                m["lowercase_currency_purchases"] += 1
                            ecom = {"total_item_quantity": sum(q for _, q in cart), "purchase_revenue_in_usd": total,
                                    "purchase_revenue": total, "shipping_value_in_usd": shipping,
                                    "unique_items": len(cart), "transaction_id": txn}
                            params = [P("currency", s=currency), P("value", d=total), P("transaction_id", s=txn),
                                      P("shipping", d=shipping), P("tax", d=0.0)]
                            emit("purchase", params, ecommerce=ecom, items=cart_items, value=total)
                            m["purchases"] += 1
                            if is_internal:
                                m["internal_purchases"] += 1
                            st["ltv"] += total
                            if r.random() < DOUBLE_PURCHASE_RATE:
                                emit("purchase", params, ecommerce=ecom, items=cart_items, value=total)
                                m["double_purchase_events"] += 1
        # session engagement: GA4 marks a session engaged after 10 s, 2 page views or a conversion
        engaged = eng_ms >= 10_000 or n_pages >= 2 or converted
        if engaged:
            events[-1]["event_params"] = events[-1]["event_params"] + [P("session_engaged", s="1")]
        # ad-platform sessions feed the spend file
        if ch_name in PAID:
            self.spend_clicks[(d, ch_name, src, campaign)] = self.spend_clicks.get((d, ch_name, src, campaign), 0) + 1
        return events

    def _channel(self, d: date) -> str:
        names = list(CHANNELS)
        w = [sum(c[3] for c in CHANNELS[n]) * campaign_boost(d, n) for n in names]
        return self.rng.choices(names, weights=w)[0]

    @staticmethod
    def _item(p, qty, list_name, idx):
        return {"item_id": p[0], "item_name": p[1], "item_brand": p[3], "item_category": p[2], "price_in_usd": p[4],
                "price": p[4], "quantity": qty, "item_revenue_in_usd": round(p[4] * qty, 2),
                "item_revenue": round(p[4] * qty, 2), "item_list_name": list_name, "item_list_index": str(idx)}

    # ------------------------------------------------------------- one day -> file(s)
    def day(self, d: date, carry: list[dict], base_sessions: int):
        n = int(base_sessions * day_multiplier(d) * self.rng.uniform(0.94, 1.06))
        rows: list[dict] = list(carry)            # late events carried from the previous day
        for _ in range(n):
            self.m["sessions"] += 1
            for ev in self.session(d):
                if self.rng.random() < NO_SESSION_ID_RATE:
                    ev["event_params"] = [p for p in ev["event_params"] if p["key"] != "ga_session_id"]
                    self.m["events_without_session_id"] += 1
                rows.append(ev)
        out, late = [], []
        for ev in rows:
            if ev["event_date"] == d.strftime("%Y%m%d") and self.rng.random() < LATE_ROW_RATE:
                late.append(ev); self.m["late_rows"] += 1
                continue
            out.append(ev)
            if self.rng.random() < DUP_ROW_RATE:
                out.append(dict(ev)); self.m["duplicate_rows"] += 1
        self.m["events"] += len(out)
        return out, late


def write_secondary(gen: Generator, out: Path, rng: random.Random, days: int) -> dict:
    sec = out / "secondary"
    sec.mkdir(parents=True, exist_ok=True)
    platform = {"Paid Search": "Google Ads", "Paid Social": "Meta Ads", "Display": "Display Network", "Email": "Newsletter tool"}
    cpc = {"Paid Search": (0.45, 0.80), "Paid Social": (0.30, 0.55), "Display": (0.15, 0.30), "Email": (0.30, 0.55)}
    drop_days = {d for d in rng.sample([START + timedelta(days=i) for i in range(days)], 2)}
    rows, negative_adjustment, name_variants = [], 0, 0
    for (d, ch, src, camp), sessions in sorted(gen.spend_clicks.items(), key=lambda kv: (kv[0][0], kv[0][1], str(kv[0][3]))):
        if ch == "Paid Social" and d in drop_days:
            continue                                   # two days missing for one platform
        clicks = int(sessions * rng.uniform(1.05, 1.25))
        lo, hi = cpc[ch]
        cost = round(clicks * rng.uniform(lo, hi), 2)
        name = camp or "(none)"
        if rng.random() < 0.10:                        # inconsistent campaign naming in the ad platform
            changed = rng.choice([name.upper(), name.replace("_", "-"), " " + name])
            if changed != name:                        # count only variants that really differ
                name_variants += 1
            name = changed
        rows.append([d.isoformat(), platform[ch], name, clicks, int(clicks * rng.uniform(25, 60)), cost, CURRENCY])
    rows.append([(START + timedelta(days=40)).isoformat(), "Google Ads", "generic_search", 0, 0, -35.0, CURRENCY])
    negative_adjustment += 1
    with open(sec / "marketing_spend.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "platform", "campaign_name", "clicks", "impressions", "cost", "currency"])
        w.writerows(rows)
    with open(sec / "product_catalog.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "item_name", "category", "brand", "list_price", "unit_cost", "launch_date"])
        for i, p in enumerate(PRODUCTS):
            w.writerow([p[0], p[1], p[2], p[3], p[4], round(p[4] * p[5], 2), (START - timedelta(days=60 + i * 9)).isoformat()])
        w.writerow([PRODUCTS[3][0], PRODUCTS[3][1], PRODUCTS[3][2], PRODUCTS[3][3], PRODUCTS[3][4],
                    round(PRODUCTS[3][4] * PRODUCTS[3][5], 2), (START - timedelta(days=87)).isoformat()])  # duplicate catalogue row
    return {"spend_rows": len(rows), "spend_days_missing_for_meta": len(drop_days),
            "spend_negative_adjustments": negative_adjustment, "spend_campaign_name_variants": name_variants,
            "catalog_duplicate_rows": 1}


def main(out_dir: str, seed: int = 42, sessions_per_day: int = 900, days: int = DAYS) -> dict:
    out = Path(out_dir)
    (out / "ga4").mkdir(parents=True, exist_ok=True)
    for old in (out / "ga4").glob("events_*.parquet"):
        old.unlink()
    gen = Generator(seed)
    carry: list[dict] = []
    for i in range(days):
        d = START + timedelta(days=i)
        rows, carry = gen.day(d, carry, sessions_per_day)
        rows.sort(key=lambda e: e["event_timestamp"])
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), out / "ga4" / f"events_{d.strftime('%Y%m%d')}.parquet",
                       compression="zstd")
    # late events left over after the last day are written to a final extra shard, as a real export would
    if carry:
        d = START + timedelta(days=days)
        carry.sort(key=lambda e: e["event_timestamp"])
        pq.write_table(pa.Table.from_pylist(carry, schema=SCHEMA), out / "ga4" / f"events_{d.strftime('%Y%m%d')}.parquet",
                       compression="zstd")
    manifest = dict(gen.m, seed=seed, start=START.isoformat(), days=days, **write_secondary(gen, out, random.Random(seed + 1), days))
    (out / "generation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sessions-per-day", type=int, default=900)
    ap.add_argument("--days", type=int, default=DAYS)
    a = ap.parse_args()
    print(json.dumps(main(a.out, a.seed, a.sessions_per_day, a.days), indent=2))
