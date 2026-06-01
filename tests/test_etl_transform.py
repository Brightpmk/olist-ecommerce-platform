import pytest
import pandas as pd

from etl.transform import _to_iso_datetime, build_fact_order_item_sales


@pytest.fixture
def mock_cleaned_data():
    return {
        "order_items": pd.DataFrame(
            {"order_id": ["o1"], "order_item_id": [1], "product_id": ["p1"],
             "seller_id": ["s1"], "price": [100.0], "freight_value": [20.0]}
        ),
        "orders": pd.DataFrame(
            {"order_id": ["o1"], "order_purchase_timestamp": ["2017-01-01 10:00:00"]}
        ),
        "products": pd.DataFrame(
            {"product_id": ["p1"], "product_category_name": ["cat1"]}
        ),
        "category_translation": pd.DataFrame(
            {"product_category_name": ["cat1"], "product_category_name_english": ["electronics"]}
        ),
    }


def test_to_iso_datetime_converts_valid_dates():
    s = pd.Series(["2017-01-01 10:30:00", "2018-02-03 05:00:00"])
    out = _to_iso_datetime(s)

    assert out.iloc[0] == "2017-01-01 10:30:00"
    assert out.iloc[1] == "2018-02-03 05:00:00"


def test_to_iso_datetime_invalid_values_become_nan():
    s = pd.Series(["not-a-date"])
    out = _to_iso_datetime(s)

    assert pd.isna(out.iloc[0])


def test_build_fact_order_item_sales_creates_expected_columns(mock_cleaned_data):
    fact = build_fact_order_item_sales(mock_cleaned_data)

    assert list(fact.columns) == [
        "order_id", "order_item_id", "seller_id", "product_id",
        "product_category_name_english", "order_purchase_timestamp",
        "price", "freight_value", "revenue",
    ]
    assert fact.iloc[0]["revenue"] == 120.0
