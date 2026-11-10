-- Daily headline numbers for the whole shop. Bots and internal traffic are excluded from every metric.
with sessions as (
    select *, session_start_ts::date as session_date
    from {{ ref('silver_ga4_sessions') }}
),

traffic as (
    select
        session_date,
        count(*)                                                      as sessions,
        count(distinct user_pseudo_id)                                as users,
        count(distinct user_pseudo_id) filter (where ga_session_number = 1) as new_users,
        count(*) filter (where is_engaged)                            as engaged_sessions,
        count(*) filter (where had_view_item)                         as sessions_with_product_view,
        count(*) filter (where had_add_to_cart)                       as sessions_with_add_to_cart,
        count(*) filter (where had_purchase)                          as purchasing_sessions
    from sessions
    where is_valid_traffic
    group by session_date
),

excluded as (
    select
        session_date,
        count(*) filter (where is_bot)                                as bot_sessions,
        count(*) filter (where is_internal and not is_bot)            as internal_sessions
    from sessions
    group by session_date
),

orders as (
    select
        purchase_date,
        count(*)                                                      as purchases,
        sum(revenue)                                                  as revenue,
        sum(revenue) filter (where session_key is null)               as unattributed_revenue
    from {{ ref('silver_ga4_purchases') }}
    where not is_internal
    group by purchase_date
),

items as (
    select purchase_date, sum(quantity) as items_sold
    from {{ ref('silver_ga4_purchase_items') }}
    where not is_internal
    group by purchase_date
)

select
    d.date_day,
    d.week_start,
    coalesce(t.sessions, 0)                                           as sessions,
    coalesce(t.users, 0)                                              as users,
    coalesce(t.new_users, 0)                                          as new_users,
    coalesce(t.engaged_sessions, 0)                                   as engaged_sessions,
    round(coalesce(t.engaged_sessions, 0) * 1.0 / nullif(t.sessions, 0), 4)   as engagement_rate,
    coalesce(t.sessions_with_product_view, 0)                         as sessions_with_product_view,
    coalesce(t.sessions_with_add_to_cart, 0)                          as sessions_with_add_to_cart,
    coalesce(t.purchasing_sessions, 0)                                as purchasing_sessions,
    round(coalesce(t.purchasing_sessions, 0) * 1.0 / nullif(t.sessions, 0), 4) as conversion_rate,
    coalesce(o.purchases, 0)                                          as purchases,
    coalesce(i.items_sold, 0)                                         as items_sold,
    round(coalesce(o.revenue, 0), 2)                                  as revenue,
    round(coalesce(o.unattributed_revenue, 0), 2)                     as unattributed_revenue,
    round(o.revenue / nullif(o.purchases, 0), 2)                      as average_order_value,
    round(coalesce(o.revenue, 0) / nullif(t.sessions, 0), 3)          as revenue_per_session,
    coalesce(x.bot_sessions, 0)                                       as bot_sessions_excluded,
    coalesce(x.internal_sessions, 0)                                  as internal_sessions_excluded
from {{ ref('dim_date') }} d
left join traffic t  on t.session_date = d.date_day
left join excluded x on x.session_date = d.date_day
left join orders o   on o.purchase_date = d.date_day
left join items i    on i.purchase_date = d.date_day
