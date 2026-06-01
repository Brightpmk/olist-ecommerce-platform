import pandas as pd
import pytest

from etl.validate import DataValidationError, validate


@pytest.fixture
def valid_data():
    return {
        "customers": pd.DataFrame(
            {"customer_id": ["c1"], "customer_unique_id": ["u1"],
             "customer_zip_code_prefix": [12345], "customer_city": ["city"], "customer_state": ["SP"]}
        ),
        "orders": pd.DataFrame(
            {"order_id": ["o1"], "customer_id": ["c1"], "order_status": ["delivered"],
             "order_purchase_timestamp": ["2017-01-01 10:00:00"], "order_approved_at": [None],
             "order_delivered_carrier_date": [None], "order_delivered_customer_date": [None],
             "order_estimated_delivery_date": [None]}
        ),
        "order_items": pd.DataFrame(
            {"order_id": ["o1"], "order_item_id": [1], "product_id": ["p1"],
             "seller_id": ["s1"], "shipping_limit_date": [None], "price": [100.0], "freight_value": [10.0]}
        ),
        "order_payments": pd.DataFrame(
            {"order_id": ["o1"], "payment_sequential": [1], "payment_type": ["credit_card"],
             "payment_installments": [1], "payment_value": [110.0]}
        ),
        "order_reviews": pd.DataFrame(
            {"review_id": ["r1"], "order_id": ["o1"], "review_score": [5],
             "review_comment_title": [None], "review_comment_message": [None],
             "review_creation_date": [None], "review_answer_timestamp": [None]}
        ),
        "products": pd.DataFrame(
            {"product_id": ["p1"], "product_category_name": ["cat1"],
             "product_name_lenght": [10], "product_description_lenght": [20],
             "product_photos_qty": [1], "product_weight_g": [100],
             "product_length_cm": [10], "product_height_cm": [10], "product_width_cm": [10]}
        ),
        "sellers": pd.DataFrame(
            {"seller_id": ["s1"], "seller_zip_code_prefix": [12345],
             "seller_city": ["city"], "seller_state": ["SP"]}
        ),
        "category_translation": pd.DataFrame(
            {"product_category_name": ["cat1"], "product_category_name_english": ["electronics"]}
        ),
        "fact_order_item_sales": pd.DataFrame(
            {"order_id": ["o1"], "order_item_id": [1], "seller_id": ["s1"],
             "product_id": ["p1"], "product_category_name_english": ["electronics"],
             "order_purchase_timestamp": ["2017-01-01 10:00:00"],
             "price": [100.0], "freight_value": [10.0], "revenue": [110.0]}
        ),
    }


def test_validate_passes_for_valid_data(valid_data):
    validate(valid_data)


def test_validate_fails_on_missing_customer_fk(valid_data):
    valid_data["orders"].loc[0, "customer_id"] = "missing_customer"

    with pytest.raises(DataValidationError):
        validate(valid_data)


def test_validate_fails_on_negative_price(valid_data):
    valid_data["order_items"].loc[0, "price"] = -1

    with pytest.raises(DataValidationError):
        validate(valid_data)
