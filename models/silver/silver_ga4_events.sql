-- One row per real event. Parameters are flattened into columns, types are fixed, placeholders become NULL,
-- exact duplicates are removed and the remaining quirks are flagged instead of dropped.
with parsed as (
    select
        make_timestamp(event_timestamp)                                              as event_ts,
        strptime(event_date, '%Y%m%d')::date                                         as event_date,
        strptime(regexp_extract(_source_file, 'events_(\d{8})', 1), '%Y%m%d')::date  as shard_date,
        event_name,
        user_pseudo_id,
        {{ ga4_param('ga_session_id', 'int') }}                                      as ga_session_id,
        {{ ga4_param('ga_session_number', 'int') }}                                  as ga_session_number,
        {{ ga4_param('page_location') }}                                             as page_location,
        {{ ga4_param('page_title') }}                                                as page_title,
        {{ ga4_param('engagement_time_msec', 'int') }}                               as engagement_time_msec,
        {{ ga4_param('source') }}                                                    as source,
        {{ ga4_param('medium') }}                                                    as medium,
        {{ ga4_param('campaign') }}                                                  as campaign,
        {{ ga4_param('traffic_type') }} = 'internal'                                 as is_internal,
        {{ ga4_param('transaction_id') }}                                            as transaction_id,
        {{ ga4_param('currency') }}                                                  as currency_raw,
        {{ ga4_param('value', 'double') }}                                           as event_value,
        {{ ga4_param('shipping', 'double') }}                                        as shipping_value,
        device.category                                                              as device_category,
        device.operating_system                                                      as operating_system,
        device.web_info.browser                                                      as browser,
        nullif(geo.country, '(not set)')                                             as country,
        nullif(geo.region, '(not set)')                                              as region,
        nullif(geo.city, '(not set)')                                                as city,
        traffic_source.source                                                        as first_touch_source,
        traffic_source.medium                                                        as first_touch_medium,
        items,
        _source_file,
        _ingested_at,
        md5(concat_ws('|',
            coalesce(user_pseudo_id, ''), event_timestamp::varchar, event_name,
            coalesce({{ ga4_param('ga_session_id', 'int') }}::varchar, ''),
            coalesce({{ ga4_param('transaction_id') }}, ''),
            coalesce({{ ga4_param('page_location') }}, '')))                         as event_key
    from {{ ref('bronze_ga4_events') }}
)

select
    * exclude (currency_raw, is_internal),
    upper(currency_raw)                              as currency,
    coalesce(is_internal, false)                     as is_internal,
    shard_date > event_date                          as is_late_arrival,
    ga_session_id is null                            as is_missing_session_id
from parsed
qualify row_number() over (partition by event_key order by _source_file, event_ts) = 1
