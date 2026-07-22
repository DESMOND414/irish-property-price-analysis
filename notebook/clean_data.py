"""
Clean the Irish Property Price Register (PPR) export into an analysis-ready dataset.

Source: propertypriceregister.ie — full history CSV, downloaded manually
(see README for the download link). Encoding is Windows-1252 (the € symbol
in "Price (€)" is stored as byte 0x80, not UTF-8).
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path("data/raw/PPR-ALL.csv")
CLEAN_PATH = Path("data/clean/properties_clean.csv")
SAMPLE_PATH = Path("data/clean/properties_sample.csv")
SUMMARY_PATH = Path("data/clean/county_year_summary.csv")

SAMPLE_SIZE = 10_000
RANDOM_SEED = 42

EIRCODE_RE = re.compile(r"^[A-Z0-9]{3}\s?[A-Z0-9]{4}$", re.IGNORECASE)


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH, encoding="cp1252", low_memory=False)
    df.columns = [
        "date_of_sale",
        "address",
        "county",
        "eircode",
        "price",
        "not_full_market_price",
        "vat_exclusive",
        "description",
        "property_size_description",
    ]
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Dates
    df["date_of_sale"] = pd.to_datetime(
        df["date_of_sale"], format="%d/%m/%Y", errors="coerce"
    )
    df["year"] = df["date_of_sale"].dt.year
    df["quarter"] = df["date_of_sale"].dt.to_period("Q").astype(str)

    # Price: strip currency symbol / thousands separators, coerce to float
    df["price"] = (
        df["price"]
        .astype(str)
        .str.replace(r"[^\d.]", "", regex=True)
        .replace("", np.nan)
        .astype(float)
    )

    # Categorical flags: "Yes"/"No" -> bool
    df["not_full_market_price"] = df["not_full_market_price"].str.strip().eq("Yes")
    df["vat_exclusive"] = df["vat_exclusive"].str.strip().eq("Yes")

    # County: normalize casing/whitespace
    df["county"] = df["county"].str.strip().str.title()

    # Eircode: keep only values that look like a real Eircode; blank otherwise
    df["eircode"] = df["eircode"].astype(str).str.strip()
    df.loc[~df["eircode"].str.match(EIRCODE_RE, na=False), "eircode"] = np.nan
    df["eircode_routing_key"] = df["eircode"].str[:3]

    # Drop rows with no usable price or date — can't analyze them
    before = len(df)
    df = df.dropna(subset=["price", "date_of_sale"])
    df = df[df["price"] > 0]
    dropped = before - len(df)

    # Outlier flag via IQR on log price (flag, don't silently delete)
    log_price = np.log1p(df["price"])
    q1, q3 = log_price.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    df["log_price"] = log_price
    df["price_outlier"] = (log_price < lower) | (log_price > upper)

    print(f"Rows in raw file: {before:,}")
    print(f"Dropped (missing/invalid price or date): {dropped:,}")
    print(f"Rows remaining: {len(df):,}")
    print(f"Flagged as price outliers: {df['price_outlier'].sum():,}")
    print(f"Flagged as 'Not Full Market Price': {df['not_full_market_price'].sum():,}")

    return df


def write_outputs(df: pd.DataFrame) -> None:
    CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_PATH, index=False)

    sample = df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=RANDOM_SEED)
    sample.to_csv(SAMPLE_PATH, index=False)

    summary = (
        df.groupby(["county", "year"])["price"]
        .agg(median_price="median", mean_price="mean", n_sales="count")
        .reset_index()
        .sort_values(["county", "year"])
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(f"\nWrote full cleaned dataset -> {CLEAN_PATH} (gitignored, local only)")
    print(f"Wrote {len(sample):,}-row sample -> {SAMPLE_PATH} (committed)")
    print(f"Wrote county/year summary -> {SUMMARY_PATH} (committed)")


if __name__ == "__main__":
    raw = load_raw()
    cleaned = clean(raw)
    write_outputs(cleaned)
