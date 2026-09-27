"""Train and evaluate the KNN and SVR admission regression models."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "dataset" / "Admission_Predict.csv"
MODEL_DIR = PROJECT_ROOT / "models"
TARGET = "Chance of Admit"
FEATURES = [
    "GRE Score",
    "TOEFL Score",
    "University Rating",
    "SOP",
    "LOR",
    "CGPA",
    "Research",
]
RANDOM_STATE = 42


def load_data() -> tuple[pd.DataFrame, pd.Series]:
    """Load the local dataset and keep the seven ordered model features."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    data = pd.read_csv(DATA_PATH)
    data.columns = data.columns.str.strip()
    data = data.drop_duplicates()

    missing_columns = set(FEATURES + [TARGET]) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {sorted(missing_columns)}")

    # Serial No. is an identifier, not a predictor.
    features = data[FEATURES]
    target = data[TARGET]
    return features, target


def build_searches() -> dict[str, tuple[GridSearchCV, str]]:
    """Create scaled regressors and small, training-only parameter searches."""
    knn_pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", KNeighborsRegressor()),
        ]
    )
    knn_search = GridSearchCV(
        estimator=knn_pipeline,
        param_grid={
            "model__n_neighbors": [3, 5, 7, 9, 11, 15],
            "model__weights": ["uniform", "distance"],
            "model__p": [1, 2],
        },
        cv=5,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
    )

    svr_pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", SVR(kernel="rbf")),
        ]
    )
    svr_search = GridSearchCV(
        estimator=svr_pipeline,
        param_grid={
            "model__C": [1, 10, 100],
            "model__epsilon": [0.03, 0.05, 0.1],
            "model__gamma": ["scale", 0.1],
        },
        cv=5,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
    )
    return {
        "KNN": (knn_search, "knn_regressor_personal"),
        "SVR": (svr_search, "svr_regressor_personal"),
    }


def evaluate_model(
    model: Pipeline, features: pd.DataFrame, target: pd.Series
) -> dict[str, float]:
    """Calculate the four required regression metrics."""
    predictions = model.predict(features)
    mse = mean_squared_error(target, predictions)
    return {
        "mae": float(mean_absolute_error(target, predictions)),
        "mse": float(mse),
        "rmse": float(mse**0.5),
        "r2": float(r2_score(target, predictions)),
    }


def train_and_save() -> pd.DataFrame:
    """Tune both models on training data, evaluate once, and save artifacts."""
    features, target = load_data()
    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=RANDOM_STATE,
    )
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for name, (search, artifact_stem) in build_searches().items():
        start = time.perf_counter()
        search.fit(X_train, y_train)
        fit_seconds = time.perf_counter() - start
        best_model = search.best_estimator_

        start = time.perf_counter()
        metrics = evaluate_model(best_model, X_test, y_test)
        predict_seconds = time.perf_counter() - start

        artifact_path = MODEL_DIR / f"{artifact_stem}.joblib"
        metadata_path = MODEL_DIR / f"{artifact_stem}_metadata.json"
        joblib.dump(best_model, artifact_path, compress=3)

        metadata = {
            "model_name": name,
            "model_version": "1.0.0",
            "artifact": artifact_path.name,
            "target": TARGET,
            "features": FEATURES,
            "random_state": RANDOM_STATE,
            "test_size": 0.2,
            "cross_validation_folds": 5,
            "best_parameters": search.best_params_,
            "best_cv_mae": float(-search.best_score_),
            "test_metrics": metrics,
            "fit_seconds_including_search": fit_seconds,
            "test_prediction_seconds": predict_seconds,
            "artifact_bytes": artifact_path.stat().st_size,
            "trained_at_utc": datetime.now(timezone.utc).isoformat(),
            "versions": {
                "scikit_learn": sklearn.__version__,
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "joblib": joblib.__version__,
            },
        }
        metadata_path.write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        rows.append(
            {
                "model": name,
                **metrics,
                "best_cv_mae": -search.best_score_,
                "best_parameters": search.best_params_,
                "fit_seconds_including_search": fit_seconds,
                "test_prediction_seconds": predict_seconds,
                "artifact": str(artifact_path.relative_to(PROJECT_ROOT)),
            }
        )

    results = pd.DataFrame(rows)
    results_path = MODEL_DIR / "personal_models_metrics.csv"
    results.to_csv(results_path, index=False)
    return results


if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    print(train_and_save().to_string(index=False))