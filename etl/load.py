from __future__ import annotations

import pandas as pd
from typing import Dict

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# category_translation gets renamed in postgres - kept the old key here so the ETL doesn't break
TABLE_NAME_MAP: Dict[str, str] = {
    "customers": "customers",
    "orders": "orders",
    "order_items": "order_items",
    "order_payments": "order_payments",
    "order_reviews": "order_reviews",
    "products": "products",
    "sellers": "sellers",
    "category_translation": "product_category_translation",
    "fact_order_item_sales": "fact_order_item_sales",
}


def load_to_postgres(database_url: str | URL, cleaned: Dict[str, pd.DataFrame]) -> None:
    engine = create_engine(database_url)

    # delete children first or FK constraints will complain
    delete_order = [
        "fact_order_item_sales",
        "order_items",
        "order_payments",
        "order_reviews",
        "orders",
        "customers",
        "products",
        "sellers",
        "product_category_translation",
    ]

    # then insert parents before children
    insert_order = [
        "customers",
        "products",
        "sellers",
        "category_translation",
        "orders",
        "order_items",
        "order_payments",
        "order_reviews",
        "fact_order_item_sales",
    ]

    with engine.connect() as conn:
        for table_name in delete_order:
            conn.execute(text(f"DELETE FROM {table_name};"))
        conn.commit()

    for key in insert_order:
        pg_table_name = TABLE_NAME_MAP[key]
        cleaned[key].to_sql(
            pg_table_name,
            engine,
            if_exists="append",
            index=False,
        )
