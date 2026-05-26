"""
Build analytics marts (star schema fact and dimension tables) from processed data.
Outputs are saved to data/marts/ directory as CSV.
"""

import os
import sys
import pandas as pd
import numpy as np

PROCESSED_PATH = "data/processed/clean_olist_data.csv"
MARTS_DIR = "data/marts"


def build_date_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Generate dim_date with one row per calendar date."""
    print("Building dim_date...")
    # Convert purchase timestamp to date
    purchase_dates = pd.to_datetime(df["order_purchase_timestamp"]).dt.date
    min_date = purchase_dates.min()
    max_date = purchase_dates.max()
    
    if pd.isna(min_date) or pd.isna(max_date):
        # Fallback if dates are empty/missing
        min_date = pd.to_datetime("2016-09-01").date()
        max_date = pd.to_datetime("2018-10-31").date()

    # Generate full date range
    date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    dim_date = pd.DataFrame({"date": date_range.date})
    dim_date["date"] = pd.to_datetime(dim_date["date"])
    
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["month"] = dim_date["date"].dt.month
    dim_date["quarter"] = dim_date["date"].dt.quarter
    dim_date["day_of_week"] = dim_date["date"].dt.day_name()
    dim_date["is_weekend"] = dim_date["day_of_week"].isin(["Saturday", "Sunday"]).astype(int)
    
    # Format date back as string for CSV key matching
    dim_date["date"] = dim_date["date"].dt.strftime("%Y-%m-%d")
    return dim_date


def build_products_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Generate unique dim_products."""
    print("Building dim_products...")
    cols = ["product_id", "product_category_name", "product_category_name_english"]
    dim_products = df[cols].drop_duplicates(subset=["product_id"]).copy()
    dim_products["product_category_name_english"] = dim_products["product_category_name_english"].fillna("unknown")
    return dim_products


def build_sellers_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Generate unique dim_sellers."""
    print("Building dim_sellers...")
    cols = ["seller_id", "seller_city", "seller_state"]
    return df[cols].drop_duplicates(subset=["seller_id"]).copy()


def calculate_rfm_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate RFM metrics and assign segment labels for customers."""
    print("Calculating RFM segments...")
    
    # Filter for delivered orders to calculate metrics accurately
    delivered = df[df["is_delivered"] == 1].copy()
    delivered["order_purchase_timestamp"] = pd.to_datetime(delivered["order_purchase_timestamp"])
    
    # Global max purchase timestamp as the reference date
    max_date = pd.to_datetime(df["order_purchase_timestamp"]).max()
    
    # Aggregate order level info per customer
    customer_orders = delivered.groupby(["customer_unique_id", "order_id"]).agg(
        order_purchase_timestamp=("order_purchase_timestamp", "first"),
        order_revenue=("revenue", "sum")
    ).reset_index()
    
    # RFM metrics calculation
    rfm = customer_orders.groupby("customer_unique_id").agg(
        last_purchase=("order_purchase_timestamp", "max"),
        frequency=("order_id", "nunique"),
        monetary=("order_revenue", "sum")
    ).reset_index()
    
    rfm["recency"] = (max_date - rfm["last_purchase"]).dt.days
    
    # Score Recency (1-5, lower recency = higher score)
    try:
        rfm["r_score"] = pd.qcut(rfm["recency"], q=5, labels=[5, 4, 3, 2, 1])
    except ValueError:
        rfm["r_score"] = pd.cut(rfm["recency"], bins=5, labels=[5, 4, 3, 2, 1])
        
    # Score Frequency (1-5, higher frequency = higher score)
    # Frequency is heavily skewed, so we assign scores based on raw frequency counts
    def get_f_score(freq):
        if freq == 1:
            return 1
        elif freq == 2:
            return 3
        else:
            return 5
            
    rfm["f_score"] = rfm["frequency"].apply(get_f_score)
    
    # Score Monetary (1-5, higher monetary = higher score)
    try:
        rfm["m_score"] = pd.qcut(rfm["monetary"], q=5, labels=[1, 2, 3, 4, 5])
    except ValueError:
        rfm["m_score"] = pd.cut(rfm["monetary"], bins=5, labels=[1, 2, 3, 4, 5])
        
    # Cast scores as integers
    rfm["r_score"] = rfm["r_score"].astype(int)
    rfm["f_score"] = rfm["f_score"].astype(int)
    rfm["m_score"] = rfm["m_score"].astype(int)
    
    rfm["rfm_score"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)
    
    # Segment assignment logic
    def assign_segment(row):
        r, f = row["r_score"], row["f_score"]
        if r >= 4 and f >= 3:
            return "Champions"
        elif r >= 3 and f >= 3:
            return "Loyal Customers"
        elif r >= 4 and f == 1:
            return "Recent Customers"
        elif r <= 2 and f >= 3:
            return "At Risk"
        elif r <= 2 and f == 1:
            return "Lost"
        elif r == 3 and f == 1:
            return "About to Sleep"
        else:
            return "Others"
            
    rfm["rfm_segment"] = rfm.apply(assign_segment, axis=1)
    
    return rfm[["customer_unique_id", "recency", "frequency", "monetary", "r_score", "f_score", "m_score", "rfm_score", "rfm_segment"]]


def build_customers_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Generate dim_customers enriched with RFM metrics and segments."""
    print("Building dim_customers...")
    cols = ["customer_unique_id", "customer_city", "customer_state"]
    dim_cust = df[cols].drop_duplicates(subset=["customer_unique_id"]).copy()
    
    # Calculate RFM
    rfm = calculate_rfm_segments(df)
    
    # Merge RFM metrics back
    dim_cust = dim_cust.merge(rfm, on="customer_unique_id", how="left")
    
    # Fill missing values for customers with no delivered orders
    dim_cust["recency"] = dim_cust["recency"].fillna(-1)
    dim_cust["frequency"] = dim_cust["frequency"].fillna(0)
    dim_cust["monetary"] = dim_cust["monetary"].fillna(0)
    dim_cust["r_score"] = dim_cust["r_score"].fillna(0).astype(int)
    dim_cust["f_score"] = dim_cust["f_score"].fillna(0).astype(int)
    dim_cust["m_score"] = dim_cust["m_score"].fillna(0).astype(int)
    dim_cust["rfm_score"] = dim_cust["rfm_score"].fillna("000")
    dim_cust["rfm_segment"] = dim_cust["rfm_segment"].fillna("Non-Active")
    
    return dim_cust


def build_fact_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Generate order-level fact_orders mart."""
    print("Building fact_orders...")
    # Group by order_id to get order-level metrics
    base = df.copy()
    base["order_purchase_timestamp"] = pd.to_datetime(base["order_purchase_timestamp"])
    
    fact_orders = (
        base.sort_values(["order_id", "order_item_id"])
        .groupby("order_id", as_index=False)
        .agg(
            customer_id=("customer_id", "first"),
            customer_unique_id=("customer_unique_id", "first"),
            order_status=("order_status", "first"),
            is_delivered=("is_delivered", "max"),
            is_canceled=("is_canceled", "max"),
            order_purchase_timestamp=("order_purchase_timestamp", "first"),
            order_date=("order_date", "first"),
            order_revenue=("revenue", "sum"),
            review_score=("review_score", "first"),
            is_late_delivery=("is_late_delivery", "max"),
            delivery_status=("delivery_status", "first"),
            delivery_delay_days=("delivery_delay_days", "first"),
            order_total_payment_value=("order_total_payment_value", "first"),
            payment_installments_max=("payment_installments_max", "first"),
            payment_type_nunique=("payment_type_nunique", "first")
        )
    )
    return fact_orders


def build_fact_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Generate item-level fact_sales mart."""
    print("Building fact_sales...")
    keep_cols = [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "customer_unique_id",
        "order_date",
        "price",
        "freight_value",
        "revenue"
    ]
    return df[keep_cols].copy()


def main() -> None:
    if not os.path.exists(PROCESSED_PATH):
        print(f"Error: Processed data not found at {PROCESSED_PATH}")
        print("Please run python analysis/scripts/build_processed_data.py first.")
        sys.exit(1)
        
    print(f"Loading processed dataset from {PROCESSED_PATH}...")
    df = pd.read_csv(PROCESSED_PATH)
    
    os.makedirs(MARTS_DIR, exist_ok=True)
    
    # Generate marts
    dim_date = build_date_dimension(df)
    dim_products = build_products_dimension(df)
    dim_sellers = build_sellers_dimension(df)
    dim_customers = build_customers_dimension(df)
    fact_orders = build_fact_orders(df)
    fact_sales = build_fact_sales(df)
    
    # Save marts
    dim_date.to_csv(os.path.join(MARTS_DIR, "dim_date.csv"), index=False)
    dim_products.to_csv(os.path.join(MARTS_DIR, "dim_products.csv"), index=False)
    dim_sellers.to_csv(os.path.join(MARTS_DIR, "dim_sellers.csv"), index=False)
    dim_customers.to_csv(os.path.join(MARTS_DIR, "dim_customers.csv"), index=False)
    fact_orders.to_csv(os.path.join(MARTS_DIR, "fact_orders.csv"), index=False)
    fact_sales.to_csv(os.path.join(MARTS_DIR, "fact_sales.csv"), index=False)
    
    print("Successfully built all analytics marts in data/marts/ folder:")
    print(" - dim_date.csv")
    print(" - dim_products.csv")
    print(" - dim_sellers.csv")
    print(" - dim_customers.csv (with RFM segments)")
    print(" - fact_orders.csv")
    print(" - fact_sales.csv")


if __name__ == "__main__":
    main()
