-- One row per item in a real purchase, taken from the deduplicated purchases.
select
    p.transaction_id,
    p.purchase_date,
    p.is_internal,
    t.i.item_id            as item_id,
    t.i.item_name          as item_name,
    t.i.item_category      as item_category,
    t.i.price              as price,
    t.i.quantity           as quantity,
    t.i.item_revenue       as item_revenue
from {{ ref('silver_ga4_purchases') }} p,
     unnest(p.items) as t(i)
