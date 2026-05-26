from __future__ import annotations

SCHEMA_TABLES: dict[str, list[str]] = {
    "dim_customers": [
        "customer_unique_id",
        "customer_city",
        "customer_state",
        "recency",
        "frequency",
        "monetary",
        "r_score",
        "f_score",
        "m_score",
        "rfm_score",
        "rfm_segment",
    ],
    "dim_products": [
        "product_id",
        "product_category_name",
        "product_category_name_english",
    ],
    "dim_sellers": [
        "seller_id",
        "seller_city",
        "seller_state",
    ],
    "dim_date": [
        "date",
        "year",
        "month",
        "quarter",
        "day_of_week",
        "is_weekend",
    ],
    "fact_orders": [
        "order_id",
        "customer_id",
        "customer_unique_id",
        "order_status",
        "is_delivered",
        "is_canceled",
        "order_purchase_timestamp",
        "order_date",
        "order_revenue",
        "review_score",
        "is_late_delivery",
        "delivery_status",
        "delivery_delay_days",
        "order_total_payment_value",
        "payment_installments_max",
        "payment_type_nunique",
    ],
    "fact_sales": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "customer_unique_id",
        "order_date",
        "price",
        "freight_value",
        "revenue",
    ],
}

SCHEMA_RELATIONSHIPS: list[str] = [
    "fact_sales.customer_unique_id = dim_customers.customer_unique_id",
    "fact_sales.product_id = dim_products.product_id",
    "fact_sales.seller_id = dim_sellers.seller_id",
    "fact_sales.order_date = dim_date.date",
    "fact_orders.customer_unique_id = dim_customers.customer_unique_id",
    "fact_orders.order_date = dim_date.date",
]

ALLOWED_TABLES = set(SCHEMA_TABLES.keys())

