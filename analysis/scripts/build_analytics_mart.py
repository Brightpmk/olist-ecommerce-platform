"""
Build analytics marts (star schema fact and dimension tables) from processed data.
Outputs are saved to data/marts/ directory as CSV and loaded directly into PostgreSQL.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Add project root to sys.path so we can import app.config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.config import Config

PROCESSED_PATH = "data/processed/clean_olist_data.csv"
MARTS_DIR = "data/marts"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def build_date_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Generate dim_date with one row per calendar date."""
    logger.info("Building dim_date...")
    purchase_dates = pd.to_datetime(df["order_purchase_timestamp"]).dt.date
    min_date = purchase_dates.min()
    max_date = purchase_dates.max()
    
    if pd.isna(min_date) or pd.isna(max_date):
        min_date = pd.to_datetime("2016-09-01").date()
        max_date = pd.to_datetime("2018-10-31").date()

    date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    dim_date = pd.DataFrame({"date": date_range.date})
    dim_date["date"] = pd.to_datetime(dim_date["date"])
    
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["month"] = dim_date["date"].dt.month
    dim_date["quarter"] = dim_date["date"].dt.quarter
    dim_date["day_of_week"] = dim_date["date"].dt.day_name()
    dim_date["is_weekend"] = dim_date["day_of_week"].isin(["Saturday", "Sunday"]).astype(int)
    
    return dim_date


def build_products_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Generate unique dim_products."""
    logger.info("Building dim_products...")
    cols = ["product_id", "product_category_name", "product_category_name_english"]
    dim_products = df[cols].drop_duplicates(subset=["product_id"]).copy()
    dim_products["product_category_name_english"] = dim_products["product_category_name_english"].fillna("unknown")
    return dim_products


def build_sellers_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Generate unique dim_sellers."""
    logger.info("Building dim_sellers...")
    cols = ["seller_id", "seller_city", "seller_state"]
    return df[cols].drop_duplicates(subset=["seller_id"]).copy()


def calculate_rfm_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate RFM metrics and assign segment labels for customers."""
    logger.info("Calculating RFM segments...")
    
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
    logger.info("Building dim_customers...")
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
    logger.info("Building fact_orders...")
    base = df.copy()
    base["order_purchase_timestamp"] = pd.to_datetime(base["order_purchase_timestamp"])
    base["order_date"] = pd.to_datetime(base["order_date"])
    
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
    logger.info("Building fact_sales...")
    base = df.copy()
    base["order_date"] = pd.to_datetime(base["order_date"])
    
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
    return base[keep_cols].copy()


def load_marts_to_postgres(marts: dict[str, pd.DataFrame]) -> None:
    """Transactionally load analytical marts to PostgreSQL database."""
    logger.info("Loading analytics marts to PostgreSQL...")
    engine = create_engine(Config.DATABASE_URL)
    
    # Dependent ordering (children first for deletion, parents first for insertion)
    delete_order = [
        "fact_sales",
        "fact_orders",
        "dim_customers",
        "dim_sellers",
        "dim_products",
        "dim_date"
    ]
    
    insert_order = [
        "dim_date",
        "dim_products",
        "dim_sellers",
        "dim_customers",
        "fact_orders",
        "fact_sales"
    ]
    
    try:
        with engine.begin() as conn:
            # Step 1: Truncate existing data in dependency-safe order
            for table in delete_order:
                logger.info(f"Truncating table {table}...")
                conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
                
            # Step 2: Load new dataset using pandas to_sql
            for table in insert_order:
                logger.info(f"Writing data to table {table} ({len(marts[table])} rows)...")
                marts[table].to_sql(
                    table,
                    conn,
                    if_exists="append",
                    index=False,
                    method="multi",
                    chunksize=5000
                )
        logger.info("Successfully loaded all marts to PostgreSQL database.")
    except Exception as e:
        logger.error(f"Error loading marts to PostgreSQL: {e}")
        raise e


def main() -> None:
    if not os.path.exists(PROCESSED_PATH):
        logger.error(f"Processed data not found at {PROCESSED_PATH}")
        sys.exit(1)
        
    logger.info(f"Loading processed dataset from {PROCESSED_PATH}...")
    df = pd.read_csv(PROCESSED_PATH)
    
    os.makedirs(MARTS_DIR, exist_ok=True)
    
    # Generate marts dataframes
    marts = {
        "dim_date": build_date_dimension(df),
        "dim_products": build_products_dimension(df),
        "dim_sellers": build_sellers_dimension(df),
        "dim_customers": build_customers_dimension(df),
        "fact_orders": build_fact_orders(df),
        "fact_sales": build_fact_sales(df)
    }
    
    # Save local CSV copies
    for name, df_mart in marts.items():
        csv_path = os.path.join(MARTS_DIR, f"{name}.csv")
        # Format date as string strictly for local CSV output
        df_csv = df_mart.copy()
        if "date" in df_csv.columns:
            df_csv["date"] = pd.to_datetime(df_csv["date"]).dt.strftime("%Y-%m-%d")
        if "order_date" in df_csv.columns:
            df_csv["order_date"] = pd.to_datetime(df_csv["order_date"]).dt.strftime("%Y-%m-%d")
            
        df_csv.to_csv(csv_path, index=False)
        logger.info(f"Saved local CSV copy to: {csv_path}")
    
    # Load to PostgreSQL
    load_marts_to_postgres(marts)
    
    logger.info("Analytics Mart pipelines completed successfully.")


if __name__ == "__main__":
    main()
