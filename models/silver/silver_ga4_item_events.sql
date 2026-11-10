-- Item views and add-to-cart events, one row per item, for the product funnel.
select
    e.event_ts::date       as event_date,
    e.event_name,
    e.is_internal,
    t.i.item_id            as item_id,
    t.i.item_category      as item_category
from {{ ref('silver_ga4_events') }} e,
     unnest(e.items) as t(i)
where e.event_name in ('view_item', 'add_to_cart')
