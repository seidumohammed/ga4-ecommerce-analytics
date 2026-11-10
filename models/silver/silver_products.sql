-- One row per product. The back-office export repeats one product, so duplicates are removed.
select
    item_id,
    item_name,
    category,
    brand,
    list_price::double   as list_price,
    unit_cost::double    as unit_cost,
    launch_date::date    as launch_date
from {{ ref('bronze_product_catalog') }}
qualify row_number() over (partition by item_id order by launch_date) = 1
