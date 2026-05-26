import pandas as pd


def format_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()

    for col in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[col]):
            formatted[col] = formatted[col].round(2)

    return formatted


def dataframe_summary(df: pd.DataFrame) -> dict:
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "is_empty": df.empty,
    }


def coerce_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    converted = df.copy()

    for col in converted.columns:
        if "date" in col.lower() or "time" in col.lower() or "month" in col.lower():
            if pd.api.types.is_numeric_dtype(converted[col]):
                continue
            try:
                converted[col] = pd.to_datetime(converted[col])
            except Exception:
                pass

    return converted
