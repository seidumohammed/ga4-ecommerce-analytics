-- Ad spend with typed columns and campaign names made to match GA4 (lower case, underscores, no stray spaces).
select
    date::date                                                   as spend_date,
    platform,
    case platform
        when 'Google Ads'      then 'Paid Search'
        when 'Meta Ads'        then 'Paid Social'
        when 'Display Network' then 'Display'
        when 'Newsletter tool' then 'Email'
    end                                                          as channel_group,
    campaign_name                                                as campaign_name_raw,
    lower(replace(trim(campaign_name), '-', '_'))                as campaign,
    clicks::bigint                                               as clicks,
    impressions::bigint                                          as impressions,
    cost::double                                                 as cost,
    upper(currency)                                              as currency,
    cost::double < 0                                             as is_adjustment
from {{ ref('bronze_marketing_spend') }}
