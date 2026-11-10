-- Events in sessions plus events with no session id must equal all cleaned events: nothing is lost between layers.
with events as (
    select count(*) as event_rows from {{ ref('silver_ga4_events') }}
),
in_sessions as (
    select sum(event_count) as session_events from {{ ref('silver_ga4_sessions') }}
),
no_session as (
    select count(*) as orphan_events from {{ ref('silver_ga4_events') }} where is_missing_session_id
)
select event_rows, session_events, orphan_events
from events, in_sessions, no_session
where event_rows <> session_events + orphan_events
