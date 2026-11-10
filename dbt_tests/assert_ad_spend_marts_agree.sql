-- The daily and weekly spend tables must hold the same total, and both must equal the cleaned source. Returns a row if not.
with daily as (select sum(spend) as total from {{ ref('mart_ad_spend_daily') }}),
weekly as (select sum(spend) as total from {{ ref('mart_channel_performance') }}),
source as (select sum(cost) as total from {{ ref('silver_marketing_spend') }})
select daily.total as daily_total, weekly.total as weekly_total, source.total as source_total
from daily, weekly, source
where abs(daily.total - source.total) > 0.05 or abs(weekly.total - source.total) > 0.05
