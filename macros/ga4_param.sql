{# Read one value out of the GA4 event_params list, for example ga4_param('ga_session_id', 'int'). #}
{% macro ga4_param(key, kind='string') -%}
    {%- set field = {'string': 'string_value', 'int': 'int_value', 'double': 'double_value'}[kind] -%}
    list_filter(event_params, lambda p: p.key = '{{ key }}')[1].value.{{ field }}
{%- endmacro %}
