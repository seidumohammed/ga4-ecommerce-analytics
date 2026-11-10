-- Weekly cohorts of users by the week of their first session, and how many come back in later weeks. Sessions
-- without a user id (consent denied) cannot be followed over time and are left out.
with activity as (
    select
        user_pseudo_id,
        date_trunc('week', session_start_ts)::date                    as active_week,
        purchase_revenue
    from {{ ref('silver_ga4_sessions') }}
    where is_valid_traffic and user_pseudo_id is not null
),

cohorts as (
    select user_pseudo_id, min(active_week) as cohort_week
    from activity
    group by 1
),

by_week as (
    select
        c.cohort_week,
        date_diff('week', c.cohort_week, a.active_week)               as weeks_since_first_visit,
        count(distinct a.user_pseudo_id)                              as active_users,
        sum(a.purchase_revenue)                                       as revenue
    from activity a
    join cohorts c using (user_pseudo_id)
    group by 1, 2
),

sizes as (
    select cohort_week, count(*) as cohort_size
    from cohorts
    group by 1
)

select
    b.cohort_week,
    b.weeks_since_first_visit,
    z.cohort_size,
    b.active_users,
    round(b.active_users * 1.0 / z.cohort_size, 4)                    as retention_rate,
    round(b.revenue, 2)                                               as revenue
from by_week b
join sizes z using (cohort_week)
