# Business brief: where the online shop wins and loses

This brief shows how the pipeline connects to decisions. The shop and its data are synthetic, and several patterns below
were built into the generator. They show the kind of answer the tables give, not findings about a real business.

## The business and the goal

An online shop sells 30 products in six categories (apparel, drinkware, bags, stationery, tech accessories and home) to
customers in Africa, the UK and the US. The goal for the quarter from October to December 2025 is
to grow revenue profitably through the peak season, without paying for traffic that does not buy.

## The questions, and which table answers each

| Who asks | Question | Table |
|---|---|---|
| Marketing lead | Which channels and campaigns pay back their spend? | `mart_channel_performance`, `mart_ad_spend_daily` |
| E-commerce manager | Where do shoppers leave the checkout, and does it differ by device? | `mart_funnel` |
| E-commerce manager | How did Black Friday change traffic and conversion? | `mart_daily_kpis`, `mart_traffic_daily` |
| Merchandising | Which products earn the most, and at what margin? | `mart_product_performance` |
| Marketing lead | Do new visitors come back? | `mart_cohort_retention` |
| Finance | Can I trust the revenue number? | `mart_data_quality`, the reconciliation tests |

## Metric definitions

| Metric | Definition |
|---|---|
| Session | A user plus a GA4 session id. Sessions with no user id are counted but cannot be linked to a person. |
| Valid session | A session that is not a bot and not internal traffic. Every gold metric uses valid sessions only. |
| Engaged session | At least 10 seconds of engagement, or 2 page views, or a purchase (the GA4 rule). |
| Conversion rate | Valid sessions with a purchase divided by valid sessions. |
| Order | One purchase per transaction id, after double-fired tags are removed. Internal test orders are excluded. |
| Revenue | Order value including shipping, in US dollars. |
| Average order value | Revenue divided by orders. |
| Return on ad spend | Revenue from the channel's sessions divided by its ad spend for the same dates. |
| Cost per order | Ad spend divided by orders from the same channel and dates. |
| Gross margin | Item revenue minus units sold times unit cost from the product catalogue. |

## What the data says

**1. The raw numbers overstate revenue.** The raw files hold 2,635 purchase rows and $169,967 of revenue. After removing
double-fired tags and internal test orders there are 2,578 orders from real customers and $166,094 of revenue, so the raw
figure is 2.3% too high. Of 101,947 sessions, 1,792 (1.8%) are bots or staff and are excluded.

**2. Black Friday week lifted revenue more than traffic.** For 24 November to 1 December, the shop averaged 1,572 sessions
a day against 1,015 in the four weeks before, up 55%. Revenue per day was $3,473 against $1,559, up 123%, because
conversion rose from 2.43% to 3.36% while the average order stayed between $63 and $66.

**3. Email is the most efficient channel, display the weakest.**

| Channel | Conversion | Return on ad spend | Cost per order |
|---|---|---|---|
| Email | 4.99% | 6.76 | $9.73 |
| Paid Search | 3.20% | 2.98 | $22.45 |
| Paid Social | 1.94% | 2.80 | $24.08 |
| Display | 0.78% | 1.65 | $33.24 |

Inside paid search, generic search (return 3.22) beat brand search (2.59), which often buys visitors who would have
arrived anyway. The Black Friday display campaign returned 1.00, the lowest of any campaign.

**4. Mobile is the biggest gap in the funnel.** Mobile is 62% of valid sessions but 43.5% of revenue. Mobile converts at
1.81% against 3.99% on desktop. The gap opens at two steps: only 11.6% of mobile sessions that view a product add one to
the cart (desktop 20.9%), and 63.6% of mobile sessions that reach payment complete the order (desktop 78.1%).

**5. Customers come back slowly.** 11.2% of a weekly cohort returns in the next week, falling to 6.3% by week four.
About 32% of sessions come from returning visitors.

## What I would do next

These are proposals to test, not forecasts.

1. **Fix mobile payment first.** If mobile payment completion rose from 63.6% to 70%, the same traffic would have produced
   about 112 more orders in the quarter, worth about $7,200 or 4.4% of revenue. Reaching the desktop rate of 78% would add
   about 253 orders and $16,200. The first step is to find out why mobile payment fails, using payment errors and
   session recordings, before changing the design.
2. **Move display budget to email and search.** Display returned $1.65 per dollar and email $6.76. Test cutting display and
   adding to the email programme, watching whether total revenue holds.
3. **Test brand search against no brand search.** Pause brand search in a few regions for two weeks and compare orders
   with the regions where it stayed on.
4. **Build a win-back email for week two.** Most returns happen in the first week, so a message in days 3 to 7 reaches
   people while they are still interested.

## What to trust and what to question

- Every number above comes from the gold tables, and the tables reconcile to each other (see the tests in the README).
- Findings 2 to 5 reflect patterns built into the generator. On a real export, check each one before acting.
- Revenue is credited to the session's own source. Multi-touch paths, view-through effects and offline sales are not
  measured here.
- The ad spend is also synthetic and was set so that returns look plausible. Real spend should be loaded from the ad
  platforms and reconciled to invoices.
