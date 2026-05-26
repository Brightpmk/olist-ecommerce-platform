import pandas as pd
from app.analytics import coerce_datetime_columns, format_dataframe

def test_coerce_datetime_columns_skips_numeric():
    # Create a dataframe with an integer month column and a string date column
    df = pd.DataFrame({
        "year": [2017, 2018],
        "month": [1, 12],
        "order_date": ["2017-01-01", "2018-12-01"],
        "revenue": [100.5, 200.75]
    })

    coerced = coerce_datetime_columns(df)

    # The 'month' column should remain an integer
    assert pd.api.types.is_integer_dtype(coerced["month"])
    assert coerced["month"].tolist() == [1, 12]

    # The 'order_date' column should be converted to datetime
    assert pd.api.types.is_datetime64_any_dtype(coerced["order_date"])
    assert coerced["order_date"].iloc[0] == pd.Timestamp("2017-01-01")

def test_format_dataframe_rounds_floats():
    df = pd.DataFrame({
        "revenue": [100.555, 200.7]
    })

    formatted = format_dataframe(df)
    assert formatted["revenue"].tolist() == [100.56, 200.7]
