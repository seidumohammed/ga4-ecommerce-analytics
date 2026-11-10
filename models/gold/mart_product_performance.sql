-- One row per product: attention, orders, revenue and margin. Rates are item-level, so cart_to_order_rate compares
-- orders with add-to-cart events for the same product and is a guide, not a session funnel.
with attention as (
    select
        item_id,
        count(*) filter (where event_name = 'view_item')              as product_views,
        count(*) filter (where event_name = 'add_to_cart')            as add_to_cart_events
    from {{ ref('silver_ga4_item_events') }}
    where not is_internal
    group by item_id
),

sales as (
    select
        item_id,
        count(distinct transaction_id)                                as orders,
        sum(quantity)                                                 as units_sold,
        sum(item_revenue)                                             as revenue
    from {{ ref('silver_ga4_purchase_items') }}
    where not is_internal
    group by item_id
)

select
    p.item_id,
    p.item_name,
    p.category,
    p.brand,
    p.list_price,
    p.unit_cost,
    coalesce(a.product_views, 0)                                      as product_views,
    coalesce(a.add_to_cart_events, 0)                                 as add_to_cart_events,
    coalesce(s.orders, 0)                                             as orders,
    coalesce(s.units_sold, 0)                                         as units_sold,
    round(coalesce(s.revenue, 0), 2)                                  as revenue,
    round(coalesce(s.units_sold, 0) * p.unit_cost, 2)                 as cost_of_goods,
    round(coalesce(s.revenue, 0) - coalesce(s.units_sold, 0) * p.unit_cost, 2) as gross_margin,
    round((coalesce(s.revenue, 0) - coalesce(s.units_sold, 0) * p.unit_cost) / nullif(s.revenue, 0), 4) as gross_margin_rate,
    round(a.add_to_cart_events * 1.0 / nullif(a.product_views, 0), 4) as view_to_cart_rate,
    round(s.orders * 1.0 / nullif(a.add_to_cart_events, 0), 4)        as cart_to_order_rate
from {{ ref('silver_products') }} p
left join attention a using (item_id)
left join sales s using (item_id)
