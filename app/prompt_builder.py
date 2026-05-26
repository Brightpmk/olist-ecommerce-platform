from app.schema import SCHEMA_RELATIONSHIPS, SCHEMA_TABLES


def build_schema_description() -> str:
    table_sections: list[str] = []

    for index, (table_name, columns) in enumerate(SCHEMA_TABLES.items(), start=1):
        column_lines = "\n".join(f"- {col}" for col in columns)
        table_sections.append(f"{index}) {table_name}\n{column_lines}")

    relationships = "\n".join(f"- {join_condition}" for join_condition in SCHEMA_RELATIONSHIPS)

    return f"""
You are generating PostgreSQL SQL for an e-commerce analytics application.

Available tables and columns:

{chr(10).join(table_sections)}

Relationships:
{relationships}

Business guidance:
- Revenue should usually be calculated from fact_sales.price or fact_orders.order_revenue. Use fact_sales for detailed product-level analysis, and fact_orders for order-level aggregations.
- Freight cost should come from fact_sales.freight_value.
- Monthly trends should use fact_orders.order_date, or join with dim_date (which contains calendar dimensions like year, month, quarter, day_of_week).
- Category names should use dim_products.product_category_name_english when available.
- For customer location distribution, use dim_customers.customer_state or dim_customers.customer_city.
- For RFM customer segmentation queries (e.g. Champions, Loyal, At Risk), query dim_customers' rfm_segment, recency, frequency, monetary, or rfm_score fields.
- For customer review scores or delivery performance (late delivery, delivery status, delay in days), query fact_orders (review_score, is_late_delivery, delivery_status, delivery_delay_days).
- For payment analysis (like installments, payment value, payment type counts), use fact_orders (order_total_payment_value, payment_installments_max, payment_type_nunique).
- For seller analysis, use dim_sellers joined via fact_sales.seller_id.

SQL generation rules:
- Generate exactly one SQL query.
- Use PostgreSQL syntax.
- Only generate SELECT queries.
- Do not generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, or REVOKE.
- Do not generate multiple statements.
- Use readable aliases.
- Add ORDER BY when useful.
- Add LIMIT 100 for non-aggregated detailed row outputs.
- Return only raw SQL. No markdown. No explanation. No code fences.
""".strip()


def build_sql_generation_prompt(user_question: str) -> str:
    return f"""
{build_schema_description()}

User business question:
{user_question}

Return only the SQL query.
""".strip()
