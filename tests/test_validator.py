import pytest
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


@pytest.mark.parametrize("sql", [
    "SELECT rfm_segment, COUNT(*) FROM dim_customers GROUP BY rfm_segment",
    "SELECT product_id, product_category_name_english FROM dim_products LIMIT 5",
    "SELECT seller_id, seller_state FROM dim_sellers LIMIT 10",
    "SELECT date, quarter FROM dim_date LIMIT 10",
    "SELECT product_id, SUM(revenue) FROM fact_sales GROUP BY product_id",
    "SELECT * FROM public.fact_orders LIMIT 5",
])
def test_allowed_tables(sql):
    ok, _ = validate_sql(sql)
    assert ok is True
