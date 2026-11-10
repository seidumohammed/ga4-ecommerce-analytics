-- Order value minus shipping must equal the sum of the item revenue. Returns a row (a failure) if the totals differ.
with orders as (
    select sum(revenue - shipping) as order_total from {{ ref('silver_ga4_purchases') }}
),
items as (
    select sum(item_revenue) as item_total from {{ ref('silver_ga4_purchase_items') }}
)
select order_total, item_total
from orders, items
where abs(order_total - item_total) > 0.05
