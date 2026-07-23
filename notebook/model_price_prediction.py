"""
Simple, honest price prediction model.

Predicts log(price) from county, property type description, and year using
a small set of models (linear regression baseline, then random forest).
The goal is to be clear about how much these three fields alone can explain
price — not to build a state-of-the-art valuation model. Property size,
condition, and BER (none of which are in the PPR export) would matter far
more in a real valuation tool.
"""

import json
import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
RESULTS_PATH = "notebook/model_results.json"
RANDOM_SEED = 42

FEATURES = ["county", "description", "year"]
TARGET = "log_price"


def load_data() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    query = f"""
        SELECT county, description, year, log_price
        FROM properties
        WHERE price_outlier = FALSE
          AND not_full_market_price = FALSE
          AND county IS NOT NULL
          AND description IS NOT NULL
          AND year IS NOT NULL
    """
    df = pd.read_sql(query, engine)
    return df


def build_pipeline(model) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["county", "description"]),
        ],
        remainder="passthrough",  # passes "year" through as-is
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def evaluate(name, pipeline, X_test, y_test) -> dict:
    preds = pipeline.predict(X_test)
    r2 = r2_score(y_test, preds)
    mae_log = mean_absolute_error(y_test, preds)
    # MAE in real euro terms is more interpretable than MAE in log-price
    mae_euro = mean_absolute_error(np.expm1(y_test), np.expm1(preds))
    print(f"{name}: R2={r2:.3f}  MAE(log)={mae_log:.3f}  MAE(EUR)={mae_euro:,.0f}")
    return {"r2": r2, "mae_log": mae_log, "mae_eur": mae_euro}


def top_features(pipeline, n=10) -> list:
    model = pipeline.named_steps["model"]
    preprocess = pipeline.named_steps["preprocess"]
    feature_names = preprocess.get_feature_names_out()
    importances = model.feature_importances_
    order = np.argsort(importances)[::-1][:n]
    return [
        {"feature": feature_names[i], "importance": round(float(importances[i]), 4)}
        for i in order
    ]


if __name__ == "__main__":
    df = load_data()
    print(f"Training rows: {len(df):,}")

    X = df[FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED
    )

    results = {}

    linreg = build_pipeline(LinearRegression())
    linreg.fit(X_train, y_train)
    results["linear_regression"] = evaluate("Linear Regression", linreg, X_test, y_test)

    rf = build_pipeline(
        RandomForestRegressor(
            n_estimators=200, max_depth=12, n_jobs=-1, random_state=RANDOM_SEED
        )
    )
    rf.fit(X_train, y_train)
    results["random_forest"] = evaluate("Random Forest", rf, X_test, y_test)
    results["random_forest"]["top_features"] = top_features(rf)

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved results -> {RESULTS_PATH}")
