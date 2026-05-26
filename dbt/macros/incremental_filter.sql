{% macro incremental_filter(outer_column, inner_column, lookback_days=3) %}
  {% if is_incremental() %}
    where {{ outer_column }} >= coalesce((select max({{ inner_column }}) - interval '{{ lookback_days }} days' from {{ this }}), '1970-01-01'::timestamp)
  {% endif %}
{% endmacro %}

