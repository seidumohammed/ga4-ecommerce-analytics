-- The traffic mart and the daily KPI mart must agree. Sessions must match every day and revenue must match over the whole
-- period. Daily revenue may differ only on days touched by a purchase made after midnight in a session that began
-- before it: mart_daily_kpis dates a purchase when it happened, mart_traffic_daily dates it when the session started.
with traffic as (
    select date_day, sum(sessions) as sessions, sum(revenue) as revenue
    from {{ ref('mart_traffic_daily') }}
    group by date_day
),

daily as (
    select
        k.date_day,
        k.sessions,
        coalesce(t.sessions, 0)                                    as traffic_sessions,
        k.revenue - k.unattributed_revenue                         as kpi_revenue,
        coalesce(t.revenue, 0)                                     as traffic_revenue
    from {{ ref('mart_daily_kpis') }} k
    left join traffic t using (date_day)
),

crossing as (
    select p.purchase_ts::date as purchase_date, s.session_start_ts::date as session_date
    from {{ ref('silver_ga4_purchases') }} p
    join {{ ref('silver_ga4_sessions') }} s using (session_key)
    where p.purchase_ts::date <> s.session_start_ts::date and not p.is_internal
),

touched_days as (
    select purchase_date as day from crossing
    union
    select session_date from crossing
)

select 'sessions differ on a day' as problem, date_day::varchar as detail
from daily
where sessions <> traffic_sessions

union all
select 'revenue differs on a day with no midnight-crossing purchase', date_day::varchar
from daily
where abs(kpi_revenue - traffic_revenue) > 0.05
  and date_day not in (select day from touched_days)

union all
select 'period revenue totals differ', (select sum(kpi_revenue) from daily)::varchar || ' vs ' || (select sum(traffic_revenue) from daily)::varchar
where abs((select sum(kpi_revenue) from daily) - (select sum(traffic_revenue) from daily)) > 0.05
