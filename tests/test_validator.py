from app.validator import validate_sql

def test_select_passes():
    ok, _ = validate_sql("SELECT * FROM fact_orders LIMIT 5")
    assert ok is True

def test_with_select_passes():
    ok, _ = validate_sql("WITH x AS (SELECT * FROM fact_orders) SELECT * FROM x")
    assert ok is True

def test_delete_rejected():
    ok, _ = validate_sql("DELETE FROM fact_orders")
    assert ok is False

def test_drop_rejected():
    ok, _ = validate_sql("DROP TABLE fact_orders")
    assert ok is False

def test_multiple_statements_rejected():
    ok, _ = validate_sql("SELECT * FROM fact_orders; DROP TABLE fact_orders;")
    assert ok is False

def test_empty_sql_rejected():
    ok, _ = validate_sql("")
    assert ok is False


def test_dim_customers_table_allowed():
    ok, _ = validate_sql("SELECT rfm_segment, COUNT(*) FROM dim_customers GROUP BY rfm_segment")
    assert ok is True


def test_dim_products_table_allowed():
    ok, _ = validate_sql(
        """
        SELECT pct.product_category_name_english, COUNT(*) AS product_count
        FROM dim_products pct
        GROUP BY pct.product_category_name_english
        """
    )
    assert ok is True


def test_dim_sellers_table_allowed():
    ok, _ = validate_sql("SELECT seller_id, seller_state FROM dim_sellers LIMIT 10")
    assert ok is True


def test_dim_date_table_allowed():
    ok, _ = validate_sql("SELECT date, quarter FROM dim_date LIMIT 10")
    assert ok is True


def test_fact_sales_table_allowed():
    ok, _ = validate_sql(
        "SELECT product_id, SUM(revenue) FROM fact_sales GROUP BY product_id"
    )
    assert ok is True

def test_schema_qualified_table_allowed():
    ok, _ = validate_sql("SELECT * FROM public.fact_orders LIMIT 5")
    assert ok is True

