import os
import sys
import yaml
import logging
import subprocess
from prefect import task, flow
from app.config import Config
from db.init_db import init_db
from etl.extract import extract_all
from etl.load import load_to_postgres
from etl.transform import transform
from etl.validate import validate
from etl.report import build_quality_report, save_quality_report

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("olist_etl_orchestrator")


def notify_failure(flow_obj, flow_run, state):
    """Mock notification hook for slack / email alerts on pipeline failure."""
    logger.error(f"!!! FLOW RUN FAILURE ALERT !!!")
    logger.error(f"Flow Name: {flow_obj.name}")
    logger.error(f"Flow Run ID: {flow_run.id}")
    logger.error(f"State Message: {state.message}")
    logger.error("ALERT: Notification successfully sent to Slack channel #data-ops and email data-alerts@olist.com")


@task
def initialize_schema_task(database_url: str):
    logger.info("Initializing database schema...")
    init_db(database_url=database_url, schema_path="db/schema.sql")


@task(retries=2, retry_delay_seconds=5)
def extract_task(raw_dir: str, tables: dict) -> dict:
    logger.info("Extracting raw CSV datasets...")
    return extract_all(raw_dir=raw_dir, tables=tables)


@task
def transform_task(dfs: dict) -> dict:
    logger.info("Running transformations...")
    return transform(dfs)


@task
def validate_task(dfs: dict, cleaned: dict, quality_report_path: str):
    logger.info("Validating clean datasets...")
    validate(cleaned)
    logger.info("Validation passed. Building data quality report...")
    report = build_quality_report(dfs, cleaned)
    save_quality_report(report, quality_report_path)


@task(retries=3, retry_delay_seconds=10)
def load_task(database_url: str, cleaned: dict):
    logger.info("Loading cleaned transactional tables to PostgreSQL...")
    load_to_postgres(database_url=database_url, cleaned=cleaned)


@task(retries=2, retry_delay_seconds=15)
def run_dbt_task():
    logger.info("Triggering dbt compile and run for analytics marts...")
    
    # Locate virtual environment python/dbt executable path
    venv_dbt = os.path.abspath(os.path.join(".venv", "Scripts", "dbt.exe"))
    if not os.path.exists(venv_dbt):
        # Fallback to general system path dbt
        venv_dbt = "dbt"
        
    cmd = [
        venv_dbt,
        "run",
        "--project-dir",
        "dbt",
        "--profiles-dir",
        "dbt"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Log stdout and stderr
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
        
    if result.returncode != 0:
        raise RuntimeError(f"dbt build failed with return code {result.returncode}")


@flow(name="Olist ETL and BI Marts Pipeline", on_failure=[notify_failure])
def olist_etl_flow():
    # Load configuration
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    raw_dir = cfg["paths"]["raw_dir"]
    tables = cfg["tables"]
    quality_report_path = cfg["paths"]["quality_report_path"]
    database_url = Config.DATABASE_URL

    # Define tasks with strict dependencies
    initialize_schema_task(database_url)
    
    raw_dfs = extract_task(raw_dir, tables)
    
    cleaned_dfs = transform_task(raw_dfs)
    
    validate_task(raw_dfs, cleaned_dfs, quality_report_path)
    
    # Load cleaned transactional data to PostgreSQL
    load_raw = load_task(database_url, cleaned_dfs)
    
    # Run dbt to rebuild public BI marts incrementally (depends on load completing)
    run_dbt_task(wait_for=[load_raw])


if __name__ == "__main__":
    olist_etl_flow()
