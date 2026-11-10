-- One row per real purchase. The tag sometimes fires twice for one order, so purchases are deduplicated on
-- transaction_id, and the number of extra firings is kept for the data-quality report.
with purchase_events as (
    select
        *,
        md5(coalesce(user_pseudo_id, 'anonymous') || '|' || ga_session_id::varchar) as session_key,
        count(*) over (partition by transaction_id) as events_for_transaction
    from {{ ref('silver_ga4_events') }}
    where event_name = 'purchase' and transaction_id is not null
)

select
    transaction_id,
    session_key,
    event_ts                                  as purchase_ts,
    event_ts::date                            as purchase_date,
    user_pseudo_id,
    currency,
    event_value                               as revenue,
    coalesce(shipping_value, 0)               as shipping,
    is_internal,
    events_for_transaction,
    items
from purchase_events
qualify row_number() over (partition by transaction_id order by event_ts) = 1
