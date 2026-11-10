-- Weekly traffic, orders and revenue by channel group and campaign, joined to ad spend. Revenue is credited to the
-- source of the session that bought (session-level last click), so purchases with no session id are not in this table.
with traffic as (
    select
        date_trunc('week', session_start_ts)::date                    as week_start,
        channel_group,
        campaign,
        count(*)                                                      as sessions,
        count(*) filter (where is_engaged)                            as engaged_sessions,
        count(*) filter (where had_purchase)                          as purchasing_sessions,
        sum(purchases)                                                as purchases,
        sum(purchase_revenue)                                         as revenue
    from {{ ref('silver_ga4_sessions') }}
    where is_valid_traffic
    group by 1, 2, 3
),

spend as (
    select
        date_trunc('week', spend_date)::date                          as week_start,
        channel_group,
        campaign,
        sum(cost)                                                     as spend,
        sum(clicks)                                                   as clicks,
        sum(impressions)                                              as impressions
    from {{ ref('silver_marketing_spend') }}
    group by 1, 2, 3
)

select
    coalesce(t.week_start, s.week_start)                              as week_start,
    coalesce(t.channel_group, s.channel_group)                        as channel_group,
    coalesce(t.campaign, s.campaign, '(none)')                        as campaign,
    coalesce(t.sessions, 0)                                           as sessions,
    coalesce(t.engaged_sessions, 0)                                   as engaged_sessions,
    coalesce(t.purchasing_sessions, 0)                                as purchasing_sessions,
    coalesce(t.purchases, 0)                                          as purchases,
    round(coalesce(t.revenue, 0), 2)                                  as revenue,
    round(coalesce(s.spend, 0), 2)                                    as spend,
    coalesce(s.clicks, 0)                                             as clicks,
    coalesce(s.impressions, 0)                                        as impressions,
    round(s.spend / nullif(t.sessions, 0), 3)                         as cost_per_session,
    round(s.spend / nullif(t.purchases, 0), 2)                        as cost_per_purchase,
    round(t.revenue / nullif(s.spend, 0), 2)                          as return_on_ad_spend
from traffic t
full outer join spend s
    on t.week_start = s.week_start
   and t.channel_group = s.channel_group
   and t.campaign is not distinct from s.campaign
