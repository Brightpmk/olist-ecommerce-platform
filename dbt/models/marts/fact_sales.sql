{{
  config(
    materialized='incremental',
    unique_key="order_id || '-' || order_item_id",
    incremental_strategy='delete+insert'
  )
}}

with base_items as (
    select
        oi.order_id,
        oi.order_item_id,
        oi.product_id,
        oi.seller_id,
        c.customer_unique_id,
        o.order_purchase_timestamp::date as order_date,
        oi.price,
        oi.freight_value,
        oi.revenue
    from {{ ref('stg_order_items') }} oi
    join {{ ref('stg_orders') }} o on oi.order_id = o.order_id
    join {{ ref('stg_customers') }} c on o.customer_id = c.customer_id
    {{ incremental_filter('o.order_purchase_timestamp', 'order_date') }}
)
select * from base_items
