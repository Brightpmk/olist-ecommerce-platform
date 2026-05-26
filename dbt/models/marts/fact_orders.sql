{{
  config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='delete+insert'
  )
}}

with base_orders as (
    select *
    from {{ ref('stg_orders') }}
    {{ incremental_filter('order_purchase_timestamp', 'order_purchase_timestamp') }}
),
order_items_agg as (
    select
        order_id,
        sum(revenue) as order_revenue
    from {{ ref('stg_order_items') }}
    group by 1
),
payments_agg as (
    select
        order_id,
        max(payment_installments) as payment_installments_max,
        count(distinct payment_type) as payment_type_nunique,
        sum(payment_value) as order_total_payment_value
    from {{ ref('stg_order_payments') }}
    group by 1
),
reviews_agg as (
    select
        order_id,
        max(review_score) as review_score
    from {{ ref('stg_order_reviews') }}
    group by 1
),
order_items_delay as (
    select
        order_id,
        case when order_status = 'delivered' and order_delivered_customer_date > order_estimated_delivery_date then 1 else 0 end as is_late_delivery,
        case
            when order_status != 'delivered' then 'not_delivered'
            when order_delivered_customer_date > order_estimated_delivery_date then 'late'
            else 'on_time_or_early'
        end as delivery_status,
        extract(epoch from (order_delivered_customer_date - order_estimated_delivery_date)) / 86400.0 as delivery_delay_days
    from base_orders
)
select
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    o.order_status,
    case when o.order_status = 'delivered' then 1 else 0 end as is_delivered,
    case when o.order_status = 'canceled' then 1 else 0 end as is_canceled,
    o.order_purchase_timestamp,
    o.order_purchase_timestamp::date as order_date,
    coalesce(oi.order_revenue, 0) as order_revenue,
    r.review_score,
    coalesce(od.is_late_delivery, 0) as is_late_delivery,
    coalesce(od.delivery_status, 'unknown') as delivery_status,
    od.delivery_delay_days,
    coalesce(p.order_total_payment_value, 0) as order_total_payment_value,
    coalesce(p.payment_installments_max, 0) as payment_installments_max,
    coalesce(p.payment_type_nunique, 0) as payment_type_nunique
from base_orders o
left join {{ ref('stg_customers') }} c on o.customer_id = c.customer_id
left join order_items_agg oi on o.order_id = oi.order_id
left join payments_agg p on o.order_id = p.order_id
left join reviews_agg r on o.order_id = r.order_id
left join order_items_delay od on o.order_id = od.order_id
