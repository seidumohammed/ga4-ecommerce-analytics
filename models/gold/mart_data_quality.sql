-- What the pipeline found and fixed, one row per issue, so every cleaning decision can be audited.
select 'raw_event_rows' as check_name, 'bronze' as layer, count(*) as rows_affected,
       'Event rows loaded from the GA4 export files' as description, 'Kept as is' as handling
from {{ ref('bronze_ga4_events') }}

union all
select 'duplicate_event_rows', 'silver',
       (select count(*) from {{ ref('bronze_ga4_events') }}) - (select count(*) from {{ ref('silver_ga4_events') }}),
       'Exact copies of an event row', 'Removed, first copy kept'

union all
select 'late_arriving_event_rows', 'silver', count(*),
       'Events written to a later day''s file than their own date', 'Kept and flagged'
from {{ ref('silver_ga4_events') }} where is_late_arrival

union all
select 'events_without_session_id', 'silver', count(*),
       'Events with no ga_session_id, so they cannot be placed in a session', 'Kept in event tables, left out of sessions'
from {{ ref('silver_ga4_events') }} where is_missing_session_id

union all
select 'consent_denied_sessions', 'silver', count(*),
       'Sessions with no user id because analytics consent was refused', 'Kept for traffic counts, left out of user counts and cohorts'
from {{ ref('silver_ga4_sessions') }} where is_consent_denied

union all
select 'bot_sessions', 'silver', count(*),
       'Non-human sessions (headless browser or very many page views)', 'Flagged and excluded from the marts'
from {{ ref('silver_ga4_sessions') }} where is_bot

union all
select 'internal_sessions', 'silver', count(*),
       'Staff and test sessions marked as internal traffic', 'Flagged and excluded from the marts'
from {{ ref('silver_ga4_sessions') }} where is_internal

union all
select 'double_fired_purchase_events', 'silver', sum(events_for_transaction - 1),
       'Extra purchase events for an order that was already recorded', 'Removed, one purchase per transaction_id'
from {{ ref('silver_ga4_purchases') }}

union all
select 'lowercase_currency_purchases', 'silver', count(*),
       'Purchases whose currency code was sent in lower case', 'Upper-cased'
from (
    select {{ ga4_param('transaction_id') }} as transaction_id
    from {{ ref('bronze_ga4_events') }}
    where event_name = 'purchase'
      and {{ ga4_param('currency') }} <> upper({{ ga4_param('currency') }})
    group by 1
) -- one count per order, even if the tag fired twice

union all
select 'catalog_duplicate_rows', 'silver',
       (select count(*) from {{ ref('bronze_product_catalog') }}) - (select count(*) from {{ ref('silver_products') }}),
       'Repeated product rows in the catalogue export', 'Removed'

union all
select 'spend_campaign_name_variants', 'silver', count(*),
       'Ad-platform campaign names that differ from the GA4 spelling (case, hyphens, spaces)', 'Standardised to lower case with underscores'
from {{ ref('silver_marketing_spend') }} where campaign_name_raw <> campaign

union all
select 'spend_negative_adjustments', 'silver', count(*),
       'Negative cost rows, which are billing adjustments', 'Kept and flagged as adjustments'
from {{ ref('silver_marketing_spend') }} where is_adjustment

union all
select 'paid_social_days_without_spend', 'silver', count(*),
       'Days with traffic but no Paid Social spend rows', 'Reported; spend for those days is understated'
from {{ ref('dim_date') }} d
where not exists (
    select 1 from {{ ref('silver_marketing_spend') }} s
    where s.channel_group = 'Paid Social' and s.spend_date = d.date_day
)
