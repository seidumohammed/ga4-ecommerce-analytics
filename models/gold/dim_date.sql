-- One row per day across the data, with the week and month used by the marts.
select
    d::date                              as date_day,
    date_trunc('week', d)::date          as week_start,
    strftime(d, '%Y-%m')                 as month,
    dayname(d)                           as day_name,
    isodow(d)                            as iso_day_of_week
from generate_series(
    (select min(session_start_ts)::date from {{ ref('silver_ga4_sessions') }}),
    (select max(session_start_ts)::date from {{ ref('silver_ga4_sessions') }}),
    interval 1 day) as t(d)
