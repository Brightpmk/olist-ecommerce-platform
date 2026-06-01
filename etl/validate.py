from __future__ import annotations

import pandas as pd


class DataValidationError(Exception):
    """Raised when cleaned data fails validation."""


def _raise(message: str) -> None:
    raise DataValidationError(message)


def _check_not_null(df: pd.DataFrame, table_name: str, columns: list[str]) -> None:
    for col in columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            _raise(f"{table_name}.{col} contains {null_count} null values")


def _check_unique(df: pd.DataFrame, table_name: str, subset: list[str]) -> None:
    dup_count = df.duplicated(subset=subset).sum()
    if dup_count > 0:
        _raise(f"{table_name} has {dup_count} duplicate rows on key {subset}")


def _check_fk(
    child_df: pd.DataFrame,
    child_table: str,
    child_col: str,
    parent_df: pd.DataFrame,
    parent_table: str,
    parent_col: str,
) -> None:
    child_values = set(child_df[child_col].dropna())
    parent_values = set(parent_df[parent_col].dropna())
    missing = child_values - parent_values
    if missing:
        _raise(
            f"Foreign key check failed: {child_table}.{child_col} -> "
            f"{parent_table}.{parent_col}. Missing references: {len(missing)}"
        )


def _check_non_negative(df: pd.DataFrame, table_name: str, columns: list[str]) -> None:
    for col in columns:
        invalid_count = (df[col] < 0).fillna(False).sum()
        if invalid_count > 0:
            _raise(f"{table_name}.{col} contains {invalid_count} negative values")


def _check_range(
    df: pd.DataFrame,
    table_name: str,
    column: str,
    min_value: int | float,
    max_value: int | float,
) -> None:
    invalid_count = ((df[column] < min_value) | (df[column] > max_value)).fillna(False).sum()
    if invalid_count > 0:
        _raise(
            f"{table_name}.{column} contains {invalid_count} values outside "
            f"allowed range [{min_value}, {max_value}]"
        )


def validate(cleaned: dict[str, pd.DataFrame]) -> None:
    customers = cleaned["customers"]
    orders = cleaned["orders"]
    order_items = cleaned["order_items"]
    order_payments = cleaned["order_payments"]
    order_reviews = cleaned["order_reviews"]
    products = cleaned["products"]
    sellers = cleaned["sellers"]
    category_translation = cleaned["category_translation"]
    fact = cleaned["fact_order_item_sales"]

    # primary keys can't be null
    _check_not_null(customers, "customers", ["customer_id"])
    _check_not_null(orders, "orders", ["order_id", "customer_id"])
    _check_not_null(order_items, "order_items", ["order_id", "order_item_id", "product_id", "seller_id"])
    _check_not_null(order_payments, "order_payments", ["order_id", "payment_sequential"])
    _check_not_null(order_reviews, "order_reviews", ["review_id", "order_id"])
    _check_not_null(products, "products", ["product_id"])
    _check_not_null(sellers, "sellers", ["seller_id"])
    _check_not_null(category_translation, "category_translation", ["product_category_name"])

    _check_unique(customers, "customers", ["customer_id"])
    _check_unique(orders, "orders", ["order_id"])
    _check_unique(order_items, "order_items", ["order_id", "order_item_id"])
    _check_unique(order_payments, "order_payments", ["order_id", "payment_sequential"])
    _check_unique(order_reviews, "order_reviews", ["review_id", "order_id"])
    _check_unique(products, "products", ["product_id"])
    _check_unique(sellers, "sellers", ["seller_id"])
    _check_unique(category_translation, "category_translation", ["product_category_name"])

    # FK checks - items ref orders/products/sellers, payments+reviews ref orders
    _check_fk(orders, "orders", "customer_id", customers, "customers", "customer_id")
    _check_fk(order_items, "order_items", "order_id", orders, "orders", "order_id")
    _check_fk(order_items, "order_items", "product_id", products, "products", "product_id")
    _check_fk(order_items, "order_items", "seller_id", sellers, "sellers", "seller_id")
    _check_fk(order_payments, "order_payments", "order_id", orders, "orders", "order_id")
    _check_fk(order_reviews, "order_reviews", "order_id", orders, "orders", "order_id")

    # prices can't be negative, scores must be 1-5
    _check_non_negative(order_items, "order_items", ["price", "freight_value"])
    _check_non_negative(order_payments, "order_payments", ["payment_value"])
    _check_range(order_reviews, "order_reviews", "review_score", 1, 5)

    # fact table should have everything after the joins
    _check_not_null(
        fact,
        "fact_order_item_sales",
        ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value", "revenue"],
    )

    if fact["order_purchase_timestamp"].isna().sum() > 0:
        _raise(
            "fact_order_item_sales.order_purchase_timestamp contains null values after joins"
        )
