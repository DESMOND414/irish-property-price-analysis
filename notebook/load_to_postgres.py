"""
Load the cleaned PPR dataset into Postgres.

Requires DATABASE_URL in a local .env file (see .env.example) pointing at a
Postgres server. Creates the target database if it doesn't exist yet, then
loads data/clean/properties_clean.csv into a `properties` table.
"""

import os
from urllib.parse import urlparse

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
CLEAN_PATH = "data/clean/properties_clean.csv"


def ensure_database_exists(database_url: str) -> None:
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")

    admin_conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname="postgres",
    )
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if cur.fetchone() is None:
            cur.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database '{db_name}'")
        else:
            print(f"Database '{db_name}' already exists")
    admin_conn.close()


def load_data(database_url: str) -> None:
    df = pd.read_csv(
        CLEAN_PATH,
        parse_dates=["date_of_sale"],
        low_memory=False,
    )
    engine = create_engine(database_url)
    df.to_sql("properties", engine, if_exists="replace", index=False, chunksize=10_000)
    print(f"Loaded {len(df):,} rows into 'properties' table")

    with engine.connect() as conn:
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_properties_county ON properties (county);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_properties_year ON properties (year);"
        )
        conn.commit()
    print("Created indexes on county and year")


if __name__ == "__main__":
    ensure_database_exists(DATABASE_URL)
    load_data(DATABASE_URL)
