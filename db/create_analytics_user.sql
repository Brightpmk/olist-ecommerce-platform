-- ============================================================
-- Dedicated Read-Only Analytics Role Configuration (PostgreSQL)
-- ============================================================

-- 1. Create a secure role with a password (replace 'bright_secure_analytics_pass_2026' with vault/env variable in production)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_analytics_user') THEN
        CREATE ROLE app_analytics_user WITH LOGIN PASSWORD 'bright_secure_analytics_pass_2026';
    END IF;
END
$$;

-- 2. Revoke default CREATE privileges on PUBLIC schema to prevent temporary table or schema modifications
REVOKE CREATE ON SCHEMA public FROM app_analytics_user;
REVOKE ALL ON DATABASE ai_analytics_ecommerce FROM app_analytics_user;

-- 3. Grant connection privileges
GRANT CONNECT ON DATABASE ai_analytics_ecommerce TO app_analytics_user;

-- 4. Grant SELECT-only usage on analytics schemas
GRANT USAGE ON SCHEMA public TO app_analytics_user;
GRANT USAGE ON SCHEMA staging TO app_analytics_user;

-- 5. Grant SELECT strictly on tables and views defined in schema.sql
GRANT SELECT ON public.customers TO app_analytics_user;
GRANT SELECT ON public.products TO app_analytics_user;
GRANT SELECT ON public.sellers TO app_analytics_user;
GRANT SELECT ON public.product_category_translation TO app_analytics_user;
GRANT SELECT ON public.orders TO app_analytics_user;
GRANT SELECT ON public.order_items TO app_analytics_user;
GRANT SELECT ON public.order_payments TO app_analytics_user;
GRANT SELECT ON public.order_reviews TO app_analytics_user;
GRANT SELECT ON public.fact_order_item_sales TO app_analytics_user;
GRANT SELECT ON public.dim_date TO app_analytics_user;
GRANT SELECT ON public.dim_products TO app_analytics_user;
GRANT SELECT ON public.dim_sellers TO app_analytics_user;
GRANT SELECT ON public.dim_customers TO app_analytics_user;
GRANT SELECT ON public.fact_orders TO app_analytics_user;
GRANT SELECT ON public.fact_sales TO app_analytics_user;

-- Grant select on all tables/views in staging for debugging/pipeline integrity
GRANT SELECT ON ALL TABLES IN SCHEMA staging TO app_analytics_user;

-- Ensure future tables/views in public/staging inherit read-only status
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_analytics_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT ON TABLES TO app_analytics_user;

-- 6. Hardening: Revoke system catalog access to prevent LLM metadata extraction/leaks
REVOKE USAGE ON SCHEMA pg_catalog FROM app_analytics_user;
REVOKE USAGE ON SCHEMA information_schema FROM app_analytics_user;

REVOKE SELECT ON ALL TABLES IN SCHEMA pg_catalog FROM app_analytics_user;
REVOKE SELECT ON ALL TABLES IN SCHEMA information_schema FROM app_analytics_user;

-- Revoke default execute on catalog functions
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM app_analytics_user;
