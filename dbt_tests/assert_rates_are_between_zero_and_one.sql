-- Every rate in the marts must be a real proportion. Returns the rows that are not.
select 'mart_daily_kpis' as model, date_day::varchar as row_key
from {{ ref('mart_daily_kpis') }}
where engagement_rate not between 0 and 1 or conversion_rate not between 0 and 1

union all
select 'mart_cohort_retention', cohort_week::varchar || ' +' || weeks_since_first_visit::varchar
from {{ ref('mart_cohort_retention') }}
where retention_rate not between 0 and 1

union all
select 'mart_product_performance', item_id
from {{ ref('mart_product_performance') }}
where view_to_cart_rate not between 0 and 1 or gross_margin_rate not between -1 and 1
