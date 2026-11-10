-- One row per session. A session is a user plus a ga_session_id, as in GA4. Traffic source and landing page come from
-- the first events of the session; engagement follows the GA4 rule (10 seconds, 2 page views or a purchase).
with events as (
    select
        *,
        md5(coalesce(user_pseudo_id, 'anonymous') || '|' || ga_session_id::varchar) as session_key
    from {{ ref('silver_ga4_events') }}
    where ga_session_id is not null
),

per_session as (
    select
        session_key,
        any_value(ga_session_id)                                                    as ga_session_id,
        any_value(user_pseudo_id)                                                   as user_pseudo_id,
        min(ga_session_number)                                                      as ga_session_number,
        min(event_ts)                                                               as session_start_ts,
        max(event_ts)                                                               as session_end_ts,
        count(*)                                                                    as event_count,
        count(*) filter (where event_name = 'page_view')                            as page_views,
        coalesce(sum(engagement_time_msec), 0)                                      as engagement_time_ms,
        arg_min(page_location, event_ts) filter (where event_name = 'page_view')    as landing_page_location,
        arg_min(source, event_ts) filter (where source is not null)                 as source,
        arg_min(medium, event_ts) filter (where medium is not null)                 as medium,
        arg_min(campaign, event_ts) filter (where campaign is not null)             as campaign,
        arg_min(device_category, event_ts)                                          as device_category,
        arg_min(browser, event_ts)                                                  as browser,
        arg_min(country, event_ts)                                                  as country,
        bool_or(is_internal)                                                        as is_internal,
        bool_or(event_name = 'view_item')                                           as had_view_item,
        bool_or(event_name = 'add_to_cart')                                         as had_add_to_cart,
        bool_or(event_name = 'begin_checkout')                                      as had_begin_checkout,
        bool_or(event_name = 'add_shipping_info')                                   as had_add_shipping_info,
        bool_or(event_name = 'add_payment_info')                                    as had_add_payment_info,
        bool_or(event_name = 'purchase')                                            as had_purchase,
        count(distinct transaction_id) filter (where event_name = 'purchase')       as purchases
    from events
    group by session_key
),

revenue as (
    select session_key, sum(revenue) as purchase_revenue
    from {{ ref('silver_ga4_purchases') }}
    group by session_key
)

select
    s.*,
    regexp_extract(s.landing_page_location, '^https?://[^/]+(/[^?#]*)', 1)                 as landing_page,
    {{ channel_group('s.source', 's.medium') }}                                            as channel_group,
    coalesce(r.purchase_revenue, 0)                                                        as purchase_revenue,
    s.user_pseudo_id is null                                                               as is_consent_denied,
    (s.browser = 'HeadlessChrome' or s.page_views >= {{ var('bot_page_view_threshold') }}) as is_bot,
    (s.engagement_time_ms >= {{ var('engaged_ms_threshold') }} or s.page_views >= 2 or s.purchases > 0) as is_engaged,
    not (s.browser = 'HeadlessChrome' or s.page_views >= {{ var('bot_page_view_threshold') }}) and not s.is_internal as is_valid_traffic
from per_session s
left join revenue r using (session_key)
