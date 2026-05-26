with date_bounds as (
    select
        min(order_purchase_timestamp)::date as min_date,
        max(order_purchase_timestamp)::date as max_date
    from {{ ref('stg_orders') }}
),
date_series as (
    select generate_series(
        (select min_date from date_bounds),
        (select max_date from date_bounds),
        '1 day'::interval
    )::date as date_day
)
select
    date_day as date,
    extract(year from date_day)::int as year,
    extract(month from date_day)::int as month,
    extract(quarter from date_day)::int as quarter,
    trim(to_char(date_day, 'Day')) as day_of_week,
    case when extract(isodow from date_day) in (6, 7) then 1 else 0 end as is_weekend
from date_series
