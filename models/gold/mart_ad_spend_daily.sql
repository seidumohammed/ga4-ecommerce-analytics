-- Daily ad spend by channel group and campaign, after the spelling of campaign names was standardised. Billing
-- adjustments (negative costs) stay in, so totals match what was invoiced.
select
    spend_date                      as date_day,
    channel_group,
    campaign,
    sum(cost)                       as spend,
    sum(clicks)                     as clicks,
    sum(impressions)                as impressions
from {{ ref('silver_marketing_spend') }}
group by 1, 2, 3
