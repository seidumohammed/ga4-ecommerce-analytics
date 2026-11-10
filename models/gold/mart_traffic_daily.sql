-- Daily traffic, orders and revenue by channel group and device. The base table for the dashboard filters.
-- Revenue is credited to the session that bought, so purchases with no session id are not here.
select
    session_start_ts::date                                as date_day,
    channel_group,
    coalesce(device_category, 'unknown')                  as device_category,
    count(*)                                              as sessions,
    count(*) filter (where is_engaged)                    as engaged_sessions,
    count(*) filter (where had_purchase)                  as purchasing_sessions,
    sum(purchases)                                        as purchases,
    round(sum(purchase_revenue), 2)                       as revenue
from {{ ref('silver_ga4_sessions') }}
where is_valid_traffic
group by 1, 2, 3
