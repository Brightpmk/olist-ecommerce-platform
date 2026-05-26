-- ============================================================
-- Olist E-commerce Platform — Unified PostgreSQL Schema
-- Merged from: olist-etl-pipeline + ecommerce-ai-analytics-assistant
-- Extended with: Star Schema BI Mart Tables DDL
-- ============================================================

-- Drop in dependency-safe order (children first)
DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS fact_orders CASCADE;
DROP TABLE IF EXISTS dim_customers CASCADE;
DROP TABLE IF EXISTS dim_sellers CASCADE;
DROP TABLE IF EXISTS dim_products CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;

DROP TABLE IF EXISTS fact_order_item_sales CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS order_payments CASCADE;
DROP TABLE IF EXISTS order_reviews CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS sellers CASCADE;
DROP TABLE IF EXISTS product_category_translation CASCADE;

-- ======================== Dimension Tables (Raw Ingestion) ========================

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    customer_zip_code_prefix INT,
    customer_city TEXT,
    customer_state TEXT
);

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_name_lenght FLOAT,
    product_description_lenght FLOAT,
    product_photos_qty FLOAT,
    product_weight_g FLOAT,
    product_length_cm FLOAT,
    product_height_cm FLOAT,
    product_width_cm FLOAT
);

CREATE TABLE sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix INT,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE product_category_translation (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

-- ======================== Transactional Tables (Raw Ingestion) ========================

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT REFERENCES customers(customer_id),
    order_status TEXT,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE order_items (
    order_id TEXT REFERENCES orders(order_id),
    order_item_id INT,
    product_id TEXT REFERENCES products(product_id),
    seller_id TEXT REFERENCES sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price NUMERIC(12,2),
    freight_value NUMERIC(12,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE order_payments (
    order_id TEXT REFERENCES orders(order_id),
    payment_sequential INT,
    payment_type TEXT,
    payment_installments INT,
    payment_value NUMERIC(12,2),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE order_reviews (
    review_id TEXT,
    order_id TEXT REFERENCES orders(order_id),
    review_score INT,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);

-- ======================== Pre-Joined Analytical Fact Table ========================

CREATE TABLE fact_order_item_sales (
    order_id TEXT,
    order_item_id INT,
    seller_id TEXT,
    product_id TEXT,
    product_category_name_english TEXT,
    order_purchase_timestamp TIMESTAMP,
    price NUMERIC(12,2),
    freight_value NUMERIC(12,2),
    revenue NUMERIC(12,2)
);

-- ======================== BI Mart Star Schema Tables ========================

CREATE TABLE dim_date (
    date DATE PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    quarter INT NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend INT NOT NULL
);

CREATE TABLE dim_products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_category_name_english TEXT
);

CREATE TABLE dim_sellers (
    seller_id TEXT PRIMARY KEY,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE dim_customers (
    customer_unique_id TEXT PRIMARY KEY,
    customer_city TEXT,
    customer_state TEXT,
    recency FLOAT NOT NULL,
    frequency INT NOT NULL,
    monetary NUMERIC(12,2) NOT NULL,
    r_score INT NOT NULL,
    f_score INT NOT NULL,
    m_score INT NOT NULL,
    rfm_score TEXT NOT NULL,
    rfm_segment TEXT NOT NULL
);

CREATE TABLE fact_orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    customer_unique_id TEXT REFERENCES dim_customers(customer_unique_id),
    order_status TEXT,
    is_delivered INT,
    is_canceled INT,
    order_purchase_timestamp TIMESTAMP,
    order_date DATE REFERENCES dim_date(date),
    order_revenue NUMERIC(12,2),
    review_score FLOAT,
    is_late_delivery INT,
    delivery_status TEXT,
    delivery_delay_days FLOAT,
    order_total_payment_value NUMERIC(12,2),
    payment_installments_max INT,
    payment_type_nunique INT
);

CREATE TABLE fact_sales (
    order_id TEXT,
    order_item_id INT,
    product_id TEXT REFERENCES dim_products(product_id),
    seller_id TEXT REFERENCES dim_sellers(seller_id),
    customer_unique_id TEXT REFERENCES dim_customers(customer_unique_id),
    order_date DATE REFERENCES dim_date(date),
    price NUMERIC(12,2),
    freight_value NUMERIC(12,2),
    revenue NUMERIC(12,2),
    PRIMARY KEY (order_id, order_item_id)
);
