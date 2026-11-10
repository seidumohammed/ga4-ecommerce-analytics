-- Each funnel step must have no more sessions than the step before it. Returns the rows that break the rule.
select *
from {{ ref('mart_funnel') }}
where product_view_sessions > sessions
   or add_to_cart_sessions > product_view_sessions
   or begin_checkout_sessions > add_to_cart_sessions
   or shipping_info_sessions > begin_checkout_sessions
   or payment_info_sessions > shipping_info_sessions
   or purchase_sessions > payment_info_sessions
