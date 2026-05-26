# Olist E-commerce Analytics Platform

> [!NOTE]
> **Consolidated Modern Data Stack Platform**
>
> This project is a unified platform created by merging three specialized systems into a production-grade Modern Data Stack (MDS):
> 1. [**olist-etl-pipeline**](https://github.com/Brightpmk/olist-etl-pipeline) — Data ingestion and validation.
> 2. [**olist-ecommerce-data-analysis**](https://github.com/Brightpmk/Basic_data-analysis-project_00) — KPI modeling and structured analytics.
> 3. [**ecommerce-ai-analytics-assistant**](https://github.com/Brightpmk/ecommerce-ai-analytics-assistant) — LLM-powered natural language interface.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![dbt](https://img.shields.io/badge/dbt-Analytics--Engineering-orange)
![Prefect](https://img.shields.io/badge/Prefect-Orchestrator-red)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector--Cache-lightgrey)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red)
![OpenAI](https://img.shields.io/badge/LLM-OpenAI-purple)
![License](https://img.shields.io/badge/License-MIT-green)

An **end-to-end e-commerce analytics platform** built on the **Olist Brazilian E-commerce dataset**. This platform automates ingestion, validates schema constraints, generates analytics marts using dbt, secures query access via a restricted read-only database role, and exposes a Streamlit-based AI assistant with a high-performance semantic query cache.

---

## Architecture

```
                           [ Kaggle Raw CSVs ]
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │             PREFECT ORCHESTRATION ENGINE                │
       │                                                         │
       │ 1. Initialize DB Schema  ──►  (postgres superuser)      │
       │ 2. Extract & Validate CSVs                              │
       │ 3. Transform & Load Raw  ──►  [PostgreSQL (staging)]    │
       │ 4. Run dbt Build Marts   ──►  [PostgreSQL (public)]     │
       └─────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │    POSTGRESQL WAREHOUSE     │
                     ├─────────────────────────────┤
                     │ staging.stg_* (Views)       │
                     │ public.dim_* (Marts)        │
                     │ public.fact_* (Marts / RFM) │
                     └──────────────┬──────────────┘
                                    │
                  Read-Only User    │ (Hardened Analytics Role)
                  app_analytics_user│
                                    ▼
                     ┌─────────────────────────────┐
                     │    AI ANALYTICS FRONTEND    │
                     │  (Streamlit App / app.py)   │
                     └──────────────┬──────────────┘
                                    │
                            ┌───────┴───────┐
                            ▼               ▼
                    [ ChromaDB Cache ]   [ OpenAI API ]
                    (Cosine Dist < 0.1)  (gpt-4o-mini)
```

---

## Key Features

### 🔄 Data Ingestion & Orchestration (Prefect)
- **Centralized Workflows**: Orchestrated using Prefect flows and tasks with explicit wait conditions and state dependency graphs.
- **Failover & Retries**: Tasks are configured with retry policies and delays to recover from transient failures.
- **Notifications**: Automated failure callbacks simulating alerts routed to Slack channels and email lists (`on_failure` hook).
- **Data Quality (Great Expectations-like)**: Auto-generates exhaustive HTML/markdown data quality reports covering type validation, null limits, and primary-key anomalies.

### 📐 Analytics Engineering (dbt)
- **Logical Layer Separation**: Raw transactional schemas are mapped as staging views (`staging.stg_*`) to preserve source layout.
- **Star Schema Marts**: Materializes dimensions (`dim_customers`, `dim_products`, `dim_sellers`, `dim_date`) and facts (`fact_orders`, `fact_sales`) in the `public` schema.
- **RFM Customer Segmentation**: Custom analytical SQL metrics calculating Recency, Frequency, and Monetary scores per customer to power marketing insights.
- **Incremental Materialization**: Fact tables utilize a custom macro (`incremental_filter`) to rebuild only the latest transactions (e.g. 3-day lookback) for fast, optimized daily runs.

### 🔒 Hardened Database Security
- **Least-Privilege Role**: Configures a dedicated `app_analytics_user` role restricted exclusively to `SELECT` access on staging views and analytics marts.
- **Catalog Obfuscation**: Revokes schema usage and select privileges from `pg_catalog` and `information_schema` systems tables to protect database metadata from structural leaks or catalog probing.

### ⚡ AI Analytics Assistant & Semantic Cache
- **Natural Language to SQL**: Converts questions into ANSI-compliant PostgreSQL queries using GPT models.
- **ChromaDB Semantic Cache**: Local vector store utilizing `text-embedding-3-small` embeddings and a strict $>90\%$ cosine similarity threshold (distance $<0.10$) to skip LLM calls, reduce costs, and serve cached SQL instantly.
- **Security Validation**: Custom SQL parser verifying queries against blacklisted modification commands (`DROP`, `DELETE`, `UPDATE`, `ALTER`, etc.) before execution.
- **Auto-Visualization**: Automatically maps query results into visual charts (bar, line, scatter) using Streamlit and Plotly.

---

## Dataset

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle)

To run this platform, download the dataset and place the raw CSV files into the `data/raw/` directory.

| File Name / Target | Description |
|--------------------|-------------|
| `olist_customers_dataset.csv` | Customer location and ZIP codes |
| `olist_orders_dataset.csv` | Order timestamps, state, and fulfillment status |
| `olist_order_items_dataset.csv` | Product IDs, seller IDs, shipping, and pricing |
| `olist_order_payments_dataset.csv`| Payment sequences, installments, and values |
| `olist_order_reviews_dataset.csv` | Customer satisfaction review scores |
| `olist_products_dataset.csv` | Product weight, categories, and dimension metrics |
| `olist_sellers_dataset.csv` | Seller location and ZIP codes |
| `product_category_name_translation.csv`| Portuguese-to-English translation mapping |

---

## Project Structure

```
olist-ecommerce-platform/
├── config/
│   └── config.yaml                 # Ingestion & quality report settings
├── db/
│   ├── schema.sql                  # Main PostgreSQL transactional schema
│   ├── init_db.py                  # Database initialization script
│   └── create_analytics_user.sql   # Hardened read-only analytics role setup
├── dbt/                            # dbt Analytics Project
│   ├── dbt_project.yml             # dbt configuration (schema mappings)
│   ├── profiles.yml                # Target connection profiles (env-injected)
│   ├── macros/
│   │   ├── generate_schema_name.sql # Custom schema compilation resolver
│   │   └── incremental_filter.sql  # High-performance incremental mart loading
│   └── models/
│       ├── staging/                # stg_*.sql views for raw tables
│       └── marts/                  # dim_*.sql and fact_*.sql analytics tables
├── etl/                            # Ingestion Sub-modules
│   ├── extract.py                  # CSV loading and directory verification
│   ├── transform.py                # Ingestion schema mapping
│   ├── validate.py                 # Out-of-bounds & data type validations
│   ├── load.py                     # PostgreSQL bulk loading
│   ├── report.py                   # Data Quality report generation
│   └── logger.py                   # Python logger configuration
├── app/                            # AI Assistant Streamlit Application
│   ├── main.py                     # Main dashboard layout and routing
│   ├── config.py                   # Environment setup configuration loader
│   ├── db.py                       # DB engine pool and query timeout controller
│   ├── llm.py                      # GPT query converter & ChromaDB cache lookup
│   ├── prompt_builder.py           # Context-aware DB prompt building
│   ├── validator.py                # SQL safety AST whitelist verification
│   ├── charts.py                   # Plotly charts generation
│   └── insights.py                 # Summary text generation using GPT
├── analysis/
│   └── scripts/
│       └── run_analysis.py         # Static reporting (generates graphs)
├── data/
│   ├── raw/                        # Kaggle raw CSV directory
│   └── chroma_cache/               # Local SQLite ChromaDB persistence folder
├── outputs/                        # Figures & summary CSV files output
├── tests/                          # Validation and profiling tests
├── main_etl.py                     # Prefect flow orchestrator entrypoint
├── requirements.txt                # Unified pip dependencies list
└── README.md
```

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Brightpmk/olist-ecommerce-platform.git
   cd olist-ecommerce-platform
   ```

2. **Set up a Python Virtual Environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate       # Windows
   source .venv/bin/activate    # macOS/Linux
   ```

3. **Install Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## Database Configuration

1. **Initialize Database and Schema**:
   Ensure PostgreSQL is running. Create a database named `ai_analytics_ecommerce`.

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```bash
   copy .env.example .env       # Windows
   cp .env.example .env         # macOS/Linux
   ```

   Configure `.env` using a write-capable database user (like `postgres` or owner) to allow the Prefect ETL flow to load transactional tables and run dbt migrations:
   ```ini
   OPENAI_API_KEY=your_openai_key_here
   MODEL_NAME=gpt-4o-mini
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ai_analytics_ecommerce
   DB_USER=postgres
   DB_PASSWORD=your_postgres_password_here
   ```

3. **Deploy Read-Only Security Role (Optional but Recommended)**:
   Connect to your database as superuser and execute the security hardening script to create `app_analytics_user`:
   ```bash
   psql -U postgres -d ai_analytics_ecommerce -f db/create_analytics_user.sql
   ```
   *Note: For highest security, update client connections in Streamlit `.env` configs to run as `app_analytics_user` with password `bright_secure_analytics_pass_2026`.*

---

## Usage

### Option A: Containerized Execution via Docker Compose (Recommended)

This is the easiest way to launch the entire stack (PostgreSQL, Prefect ETL/dbt orchestrator, and Streamlit AI Assistant) without manual local database setups.

1. **Build and start the database and web assistant**:
   ```bash
   docker-compose up --build -d db assistant
   ```

2. **Trigger the Orchestrated Ingestion & dbt Marts Pipeline**:
   ```bash
   docker-compose run --rm etl
   ```
   *Note: This service waits for the database container to be healthy, validates raw inputs, populates the transactional tables, and runs dbt transforms in one go.*

3. **Access the Frontend App**:
   Open [http://localhost:8501](http://localhost:8501) in your browser.

---

### Option B: Local Manual Execution

If you prefer to run the components directly on your host machine:

1. **Run the Ingestion & Transformation Flow**
   Execute the Prefect orchestrator to initialize schemas, clean and validate inputs, load transactional tables, and compile dbt analytical marts:
   ```bash
   python main_etl.py
   ```

2. **Run Standalone dbt Executions**
   To compile and run models directly in your local PostgreSQL workspace:
   ```bash
   cd dbt
   dbt run --profiles-dir .
   ```

3. **Generate Static Analytical Insights**
   Generate static charts and summary tables from the PostgreSQL marts directly into the `outputs/` folder:
   ```bash
   python analysis/scripts/run_analysis.py
   ```

4. **Launch the AI Assistant Streamlit Web App**
   Start the conversational user interface:
   ```bash
   python -m streamlit run app/main.py
   ```

---

## Testing

Run unit tests to verify transformations, validator parsing rules, schema profilers, and assistant mechanisms:
```bash
pytest
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
