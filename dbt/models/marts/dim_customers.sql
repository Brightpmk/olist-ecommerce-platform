with delivered_orders as (
    select
        o.order_id,
        o.customer_id,
        c.customer_unique_id,
        o.order_purchase_timestamp,
        c.customer_city,
        c.customer_state
    from {{ ref('stg_orders') }} o
    join {{ ref('stg_customers') }} c on o.customer_id = c.customer_id
    where o.order_status = 'delivered'
),
order_revenues as (
    select
        order_id,
        sum(revenue) as order_revenue
    from {{ ref('stg_order_items') }}
    group by 1
),
delivered_with_revenue as (
    select
        d.*,
        coalesce(r.order_revenue, 0) as order_revenue
    from delivered_orders d
    left join order_revenues r on d.order_id = r.order_id
),
max_date_ref as (
    select max(order_purchase_timestamp) as global_max_date
    from {{ ref('stg_orders') }}
),
customer_rfm as (
    select
        d.customer_unique_id,
        extract(epoch from ((select global_max_date from max_date_ref) - max(d.order_purchase_timestamp))) / 86400.0 as recency,
        count(distinct d.order_id) as frequency,
        sum(d.order_revenue) as monetary
    from delivered_with_revenue d
    group by 1
),
scored_rfm as (
    select
        customer_unique_id,
        recency,
        frequency,
        monetary,
        ntile(5) over (order by recency desc) as r_score,
        case
            when frequency = 1 then 1
            when frequency = 2 then 3
            else 5
        end as f_score,
        ntile(5) over (order by monetary asc) as m_score
    from customer_rfm
),
segmented_rfm as (
    select
        customer_unique_id,
        recency,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        concat(r_score::text, f_score::text, m_score::text) as rfm_score,
        case
            when r_score >= 4 and f_score >= 3 then 'Champions'
            when r_score >= 3 and f_score >= 3 then 'Loyal Customers'
            when r_score >= 4 and f_score = 1 then 'Recent Customers'
            when r_score <= 2 and f_score >= 3 then 'At Risk'
            when r_score <= 2 and f_score = 1 then 'Lost'
            when r_score = 3 and f_score = 1 then 'About to Sleep'
            else 'Others'
        end as rfm_segment
    from scored_rfm
),
all_customers as (
    select distinct
        customer_unique_id,
        customer_city,
        customer_state
    from {{ ref('stg_customers') }}
)
select
    ac.customer_unique_id,
    ac.customer_city,
    ac.customer_state,
    coalesce(sr.recency, -1) as recency,
    coalesce(sr.frequency, 0) as frequency,
    coalesce(sr.monetary, 0) as monetary,
    coalesce(sr.r_score, 0) as r_score,
    coalesce(sr.f_score, 0) as f_score,
    coalesce(sr.m_score, 0) as m_score,
    coalesce(sr.rfm_score, '000') as rfm_score,
    coalesce(sr.rfm_segment, 'Non-Active') as rfm_segment
from all_customers ac
left join segmented_rfm sr on ac.customer_unique_id = sr.customer_unique_id
