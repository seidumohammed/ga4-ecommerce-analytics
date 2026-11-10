-- Revenue credited to channels plus revenue with no session id must equal the daily total. A gap means money is lost
-- or counted twice between the daily and channel marts.
with channels as (
    select sum(revenue) as channel_revenue from {{ ref('mart_channel_performance') }}
),
daily as (
    select sum(revenue) as total_revenue, sum(unattributed_revenue) as unattributed from {{ ref('mart_daily_kpis') }}
)
select channel_revenue, unattributed, total_revenue
from channels, daily
where abs(channel_revenue + unattributed - total_revenue) > 0.05
