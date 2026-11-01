"""Order-placement prediction, temporal validation and fingerprinted local artifacts."""
from hashlib import sha256
from pathlib import Path
import json
import platform
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             confusion_matrix, roc_auc_score, average_precision_score,
                             brier_score_loss)
from sklearn.calibration import calibration_curve

SCHEMA_VERSION = "order-placement-v1.2"
NUMERIC = ["sales", "quantity", "discount", "scheduled_days", "order_month", "order_weekday"]
CATEGORICAL = ["region", "category", "shipping_mode", "segment"]
FEATURES = NUMERIC + CATEGORICAL
SEED = 21

def dataset_fingerprint(orders):
    stable = orders.sort_values("order_id").reset_index(drop=True)
    payload = pd.util.hash_pandas_object(stable, index=False).values.tobytes()
    return sha256(payload + (SCHEMA_VERSION + sklearn.__version__ + str(SEED)).encode()).hexdigest()

def feature_audit(orders):
    included = [c for c in FEATURES if c in orders and orders[c].notna().any()]
    rows = []
    for col in orders.columns:
        if col in included:
            why = "Order-placement input; availability must be confirmed for uploaded sources."
            if col == "scheduled_days":
                why = "Promise shown at checkout; uses promised date, never actual outcome."
            if col in {"order_month", "order_weekday"}:
                why = "Calendar feature derived only from order placement date."
            rows.append({"field": col, "decision": "Included", "reason": why})
        else:
            rows.append({"field": col, "decision": "Excluded",
                         "reason": "Identifier, administrative field, outcome, post-delivery value or unsupported input."})
    return pd.DataFrame(rows)

def feature_frame(orders, features):
    x = orders[features].copy()
    for col in features:
        if col in CATEGORICAL:
            x[col] = x[col].astype(object).where(x[col].notna(), np.nan)
        else:
            x[col] = pd.to_numeric(x[col], errors="coerce").astype(float)
    return x

def temporal_split(orders):
    data = orders.loc[orders.eligible].sort_values(["order_date", "order_id"]).copy()
    if data.order_id.duplicated().any():
        raise ValueError("Training requires exactly one row per order.")
    if len(data) < 300:
        raise ValueError("At least 300 eligible orders are required for chronological modeling.")
    if data.late.nunique() < 2:
        raise ValueError("A single-class target cannot support this classification comparison.")
    days = np.sort(data.order_date.dt.normalize().unique())
    if len(days) < 30:
        raise ValueError("At least 30 distinct order dates are required for temporal evaluation.")
    validation_start = pd.Timestamp(days[int(len(days)*.6)])
    test_start = pd.Timestamp(days[int(len(days)*.8)])
    order_day = data.order_date.dt.normalize()
    known_at = data.delivery_date.dt.normalize() + pd.to_timedelta(np.ones(len(data), dtype=int), unit="D")
    missing_date = known_at.isna()
    known_at.loc[missing_date] = data.loc[missing_date, "order_date"].dt.normalize() + pd.to_timedelta(data.loc[missing_date, "actual_days"] + 1, unit="D")
    train_mask = order_day.lt(validation_start)
    validation_mask = order_day.ge(validation_start) & order_day.lt(test_start)
    train = data.loc[train_mask & known_at.lt(validation_start)]
    validation = data.loc[validation_mask & known_at.lt(test_start)]
    test = data.loc[order_day.ge(test_start)]
    for label, split in [("train", train), ("validation", validation), ("test", test)]:
        counts = split.late.value_counts()
        if len(split) < 50 or len(counts) < 2 or counts.min() < 3:
            raise ValueError(f"Insufficient class coverage in {label}; need 50 orders and at least 3 per class.")
    metadata = {
        "method": "Chronological 60/20/20 of distinct order dates, with label-availability purge.",
        "validation_start": str(validation_start.date()), "test_start": str(test_start.date()),
        "purged_train_orders": int(train_mask.sum() - len(train)),
        "purged_validation_orders": int(validation_mask.sum() - len(validation)),
        "label_availability": "Customer delivery calendar date + 1 day; duration-only uploads use order date + actual days + 1.",
        "splits": {}
    }
    for label, split in [("train", train), ("validation", validation), ("test", test)]:
        metadata["splits"][label] = {"rows": len(split), "orders": split.order_id.nunique(),
                                   "start": str(split.order_date.min().date()),
                                   "end": str(split.order_date.max().date()),
                                   "late_orders": int(split.late.sum()),
                                   "late_rate": float(split.late.mean())}
    return train, validation, test, metadata

def evaluate(y, probability, threshold):
    pred = (probability >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probability)) if len(np.unique(y)) == 2 else None,
        "pr_auc_ap": float(average_precision_score(y, probability)) if np.sum(y) else None,
        "brier_score": float(brier_score_loss(y, probability)),
        "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
    }

def train_models(orders, placement_confirmed=False):
    if int(orders.eligible.sum()) > 100000:
        raise ValueError("Local training supports up to 100,000 eligible orders. Supply a representative order-level CSV within this limit; descriptive analysis remains available.")
    if not placement_confirmed:
        raise ValueError("Confirm feature availability at order placement before training.")
    if orders.label_mismatch.any():
        raise ValueError("Supplied late labels disagree with derived outcomes. Resolve the mismatch before training.")
    train, validation, test, split_metadata = temporal_split(orders)
    features = [c for c in FEATURES if c in train and train[c].notna().any()]
    if "scheduled_days" not in features:
        raise ValueError("A usable checkout delivery promise is required.")
    numeric = [c for c in features if c in NUMERIC]
    categorical = [c for c in features if c in CATEGORICAL]
    x_train, x_val, x_test = [feature_frame(s, features) for s in [train, validation, test]]
    y_train, y_val, y_test = [s.late.astype(int).to_numpy() for s in [train, validation, test]]
    weight = "balanced" if min(y_train.mean(), 1-y_train.mean()) < .2 else None
    estimators = {
        "Dummy baseline": DummyClassifier(strategy="prior"),
        "Logistic Regression": LogisticRegression(max_iter=1500, class_weight=weight, random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=120, max_depth=10, min_samples_leaf=8,
                                               class_weight=weight, random_state=SEED, n_jobs=2),
    }
    fitted, validation_results, thresholds = {}, {}, {}
    for name, estimator in estimators.items():
        transform = ColumnTransformer([
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
            ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                                      ("encode", OneHotEncoder(handle_unknown="ignore"))]), categorical),
        ])
        model = Pipeline([("prepare", transform), ("classifier", estimator)])
        model.fit(x_train, y_train)
        prob = model.predict_proba(x_val)[:, 1]
        if name == "Dummy baseline":
            threshold = .5
        else:
            candidates = np.arange(.05, .81, .05)
            threshold = float(max(candidates, key=lambda t: (f1_score(y_val, prob >= t, zero_division=0), t)))
        thresholds[name] = threshold
        validation_results[name] = evaluate(y_val, prob, threshold)
        fitted[name] = model
    candidates = [n for n in fitted if n != "Dummy baseline"]
    selected = max(candidates, key=lambda name: (validation_results[name]["pr_auc_ap"], validation_results[name]["f1"]))
    # Only now use test labels. No fitting or threshold changes follow this step.
    test_results = {name: evaluate(y_test, model.predict_proba(x_test)[:, 1], thresholds[name])
                    for name, model in fitted.items()}
    probability = fitted[selected].predict_proba(x_test)[:, 1]
    fraction, average = calibration_curve(y_test, probability, n_bins=6, strategy="quantile")
    names = fitted["Logistic Regression"].named_steps["prepare"].get_feature_names_out()
    coefs = fitted["Logistic Regression"].named_steps["classifier"].coef_[0]
    explanations = sorted([{"feature": str(n), "coefficient": float(c)} for n, c in zip(names, coefs)],
                          key=lambda row: abs(row["coefficient"]), reverse=True)[:15]
    bounds, categories = {}, {}
    for col in numeric:
        bounds[col] = [float(x_train[col].min()), float(x_train[col].max())]
    for col in categorical:
        categories[col] = sorted(x_train[col].dropna().astype(str).unique().tolist())
    report = {
        "schema_version": SCHEMA_VERSION, "fingerprint": dataset_fingerprint(orders),
        "python": platform.python_version(), "sklearn": sklearn.__version__,
        "target": "1 if delivered on a later calendar date than the checkout promise, otherwise 0; eligible delivered orders only.",
        "prediction_moment": "Order placement, conditional on eventual observed delivery.",
        "features": features, "split": split_metadata, "class_weight": weight,
        "selection": "Highest validation average precision (AP); validation F1 tie-break. Threshold maximizes validation F1 over 0.05 to 0.80.",
        "selected_model": selected, "threshold": thresholds[selected],
        "thresholds": thresholds, "validation": validation_results, "test": test_results,
        "calibration": {"mean_predicted": average.tolist(), "observed_late_fraction": fraction.tolist(),
                        "note": "Held-out reliability bins and Brier score assess calibration; probabilities are not guaranteed confidence. No post-hoc calibrator fitted."},
        "logistic_coefficients": explanations, "training_bounds": bounds, "training_categories": categories,
        "limitations": [
            "Historical observational sample; performance can drift across time, states and products.",
            "Only orders with observed delivery outcomes are modeled; cancellation and non-delivery risk are outside the target.",
            "Label timing uses delivery day + 1 day; administrative reporting delays are unknown.",
            "Checkout availability of price, quantity, category and promise is assumed for Olist; confirm for uploaded data.",
            "F1 thresholds reflect a heuristic, not a measured business cost or guaranteed service improvement.",
            "Coefficients describe associations in the Logistic Regression comparator and are not causal effects.",
        ],
    }
    return {"model": fitted[selected], "report": report}

def predict_batch(bundle, frame):
    report = bundle["report"]
    features = report["features"]
    missing = [c for c in features if c not in frame]
    if missing:
        raise ValueError("Missing mandatory inputs: " + ", ".join(missing))
    data = frame[features].copy()
    warnings = [[] for _ in range(len(data))]
    for col in features:
        if data[col].isna().any() or data[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Missing mandatory values in {col}.")
        if col in NUMERIC:
            values = pd.to_numeric(data[col], errors="coerce")
            if values.isna().any() or not np.isfinite(values).all():
                raise ValueError(f"{col} must contain finite numbers.")
            if col in {"sales", "scheduled_days"} and values.lt(0).any():
                raise ValueError(f"{col} cannot be negative.")
            if col == "quantity" and ((values < 1) | (values % 1 != 0)).any():
                raise ValueError("quantity must be a positive integer.")
            if col == "discount" and (~values.between(0, 1)).any():
                raise ValueError("discount must be in [0, 1].")
            if col in {"order_month", "order_weekday"}:
                low, high = (1, 12) if col == "order_month" else (0, 6)
                if ((values % 1 != 0) | ~values.between(low, high)).any():
                    raise ValueError(f"{col} must be an integer between {low} and {high}.")
            a, b = report["training_bounds"][col]
            for i, val in enumerate(values):
                if val < a or val > b:
                    warnings[i].append(f"{col} outside training range [{a:g}, {b:g}]")
            data[col] = values
        else:
            data[col] = data[col].astype(str).str.strip()
            if data[col].str.len().gt(120).any():
                raise ValueError(f"{col} exceeds 120 characters.")
            for i, val in enumerate(data[col]):
                if val not in report["training_categories"][col]:
                    warnings[i].append(f"Unseen {col}: estimate may be unreliable")
    probability = bundle["model"].predict_proba(feature_frame(data, features))[:, 1]
    return pd.DataFrame({"submitted_row": np.arange(1, len(data)+1), "late_risk": probability,
                         "predicted_class": np.where(probability >= report["threshold"], "Late", "On time"),
                         "threshold": report["threshold"], "warnings": ["; ".join(w) for w in warnings]})

def save_local_bundle(bundle, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, directory / "sample_model.joblib", compress=3)
    (directory / "model_evaluation.json").write_text(json.dumps(bundle["report"], indent=2), encoding="utf-8")

def load_local_bundle(directory, orders):
    # Fixed trusted path only; no uploaded joblib/pickle support.
    directory = Path(directory)
    metadata = directory / "model_evaluation.json"
    model_path = directory / "sample_model.joblib"
    if not metadata.exists() or not model_path.exists():
        return None
    report = json.loads(metadata.read_text(encoding="utf-8"))
    if report.get("fingerprint") != dataset_fingerprint(orders) or report.get("schema_version") != SCHEMA_VERSION or report.get("sklearn") != sklearn.__version__:
        return None
    bundle = joblib.load(model_path)
    if bundle["report"]["fingerprint"] != report["fingerprint"]:
        return None
    return bundle