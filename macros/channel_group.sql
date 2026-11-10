{# A simplified version of the GA4 default channel group, from source and medium. #}
{% macro channel_group(source, medium) -%}
    case
        when lower({{ source }}) = '(direct)' and (lower({{ medium }}) in ('(none)', '(not set)') or {{ medium }} is null) then 'Direct'
        when lower({{ medium }}) in ('paid_social', 'paidsocial', 'paid-social')
          or (lower({{ medium }}) in ('cpc', 'ppc') and lower({{ source }}) in ('facebook', 'instagram', 'tiktok', 'twitter', 'linkedin')) then 'Paid Social'
        when lower({{ medium }}) in ('cpc', 'ppc', 'paidsearch') then 'Paid Search'
        when lower({{ medium }}) in ('display', 'banner', 'expandable', 'interstitial', 'cpm') then 'Display'
        when lower({{ medium }}) in ('email', 'e-mail', 'e_mail', 'e mail') then 'Email'
        when lower({{ medium }}) = 'organic' then 'Organic Search'
        when lower({{ medium }}) in ('social', 'social-network', 'social-media', 'sm', 'social network', 'social media') then 'Organic Social'
        when lower({{ medium }}) in ('referral', 'app', 'link') then 'Referral'
        else 'Unassigned'
    end
{%- endmacro %}
