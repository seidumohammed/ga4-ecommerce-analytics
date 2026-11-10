-- Daily checkout funnel by device and channel group. A session counts for a step if it reached that step or any later
-- one, so a lost tracking event cannot make a later step larger than an earlier one.
with flags as (
    select
        session_start_ts::date                                        as session_date,
        coalesce(device_category, 'unknown')                          as device_category,
        channel_group,
        (had_view_item or had_add_to_cart or had_begin_checkout or had_add_shipping_info or had_add_payment_info or had_purchase)
                                                                      as reached_product_view,
        (had_add_to_cart or had_begin_checkout or had_add_shipping_info or had_add_payment_info or had_purchase)
                                                                      as reached_add_to_cart,
        (had_begin_checkout or had_add_shipping_info or had_add_payment_info or had_purchase)
                                                                      as reached_begin_checkout,
        (had_add_shipping_info or had_add_payment_info or had_purchase)
                                                                      as reached_shipping_info,
        (had_add_payment_info or had_purchase)                        as reached_payment_info,
        had_purchase                                                  as reached_purchase
    from {{ ref('silver_ga4_sessions') }}
    where is_valid_traffic
)

select
    session_date,
    device_category,
    channel_group,
    count(*)                                                          as sessions,
    count(*) filter (where reached_product_view)                      as product_view_sessions,
    count(*) filter (where reached_add_to_cart)                       as add_to_cart_sessions,
    count(*) filter (where reached_begin_checkout)                    as begin_checkout_sessions,
    count(*) filter (where reached_shipping_info)                     as shipping_info_sessions,
    count(*) filter (where reached_payment_info)                      as payment_info_sessions,
    count(*) filter (where reached_purchase)                          as purchase_sessions
from flags
group by 1, 2, 3
