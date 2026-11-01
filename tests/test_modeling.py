"""Model boundary, leakage, temporal order, inference and artifact checks."""
import json
import numpy as np
import pandas as pd
import pytest
from src.validation import prepare_orders
from src.modeling import (train_models, temporal_split, predict_batch, feature_audit,
                          save_local_bundle, load_local_bundle, dataset_fingerprint)

@pytest.fixture(scope="module")
def training_orders():
    rng = np.random.default_rng(21)
    n = 700
    dates = pd.date_range("2022-01-01", periods=n)
    late = rng.random(n) < .23
    raw = pd.DataFrame({
        "order_id":[f"SYNTHETIC-{i}" for i in range(n)],
        "order_date": dates.strftime("%Y-%m-%d"),
        "delivery_date": (dates + pd.to_timedelta(np.where(late,9,4), unit="D")).strftime("%Y-%m-%d"),
        "promised_date": (dates + pd.Timedelta(days=6)).strftime("%Y-%m-%d"),
        "status":"delivered", "sales":rng.integers(10,300,size=n), "quantity":1,
        "category":np.where(late, "Games","Books"), "region":np.where(np.arange(n)%2, "North","South")
    })
    # Synthetic fixture is used only to test behavior, never as real business evidence.
    return prepare_orders(raw).orders

@pytest.fixture(scope="module")
def trained(training_orders):
    return train_models(training_orders, placement_confirmed=True)

def test_split_has_no_order_overlap_and_no_future_outcomes(training_orders):
    train,val,test,meta = temporal_split(training_orders)
    assert not set(train.order_id) & set(val.order_id)
    assert not set(train.order_id) & set(test.order_id)
    assert not set(val.order_id) & set(test.order_id)
    assert train.order_date.max() < val.order_date.min() < test.order_date.min()
    assert (train.delivery_date.dt.normalize()+pd.Timedelta(days=1) < pd.Timestamp(meta["validation_start"])).all()
    assert (val.delivery_date.dt.normalize()+pd.Timedelta(days=1) < pd.Timestamp(meta["test_start"])).all()

def test_feature_allowlist_excludes_leakage(training_orders, trained):
    forbidden={"order_id","actual_days","delivery_date","delay_days","late","status","delivery_outcome","profit","supplied_late"}
    assert not forbidden & set(trained["report"]["features"])
    audit = feature_audit(training_orders).set_index("field")
    assert audit.loc["actual_days","decision"] == "Excluded"

def test_confirm_placement_required(training_orders):
    with pytest.raises(ValueError, match="Confirm"):
        train_models(training_orders)

def test_too_few_and_single_class(training_orders):
    with pytest.raises(ValueError, match="300"):
        temporal_split(training_orders.head(100))
    single = training_orders.copy()
    single["late"] = 0
    with pytest.raises(ValueError, match="single-class"):
        temporal_split(single)

def test_mismatched_labels_block(training_orders):
    data = training_orders.copy()
    data.loc[0,"label_mismatch"] = True
    with pytest.raises(ValueError, match="disagree"):
        train_models(data, placement_confirmed=True)

def test_unseen_categories_and_preserved_rows(training_orders, trained):
    frame = training_orders[trained["report"]["features"]].iloc[:2].copy()
    frame.index = [90,12]
    frame.iloc[0,frame.columns.get_loc("region")] = "Unseen destination"
    result = predict_batch(trained, frame)
    assert result.submitted_row.tolist() == [1,2]
    assert "Unseen region" in result.warnings.iloc[0]
    assert result.late_risk.between(0,1).all()

def test_prediction_validation(training_orders, trained):
    frame = training_orders[trained["report"]["features"]].iloc[:1].copy()
    with pytest.raises(ValueError, match="Missing mandatory"):
        predict_batch(trained, frame.drop(columns=["scheduled_days"]))
    frame["sales"] = -1
    with pytest.raises(ValueError, match="negative"):
        predict_batch(trained, frame)
    frame["sales"] = 10000000
    assert "outside training range" in predict_batch(trained,frame).warnings.iloc[0]

def test_versioned_artifact_invalidation(tmp_path, training_orders, trained):
    save_local_bundle(trained,tmp_path)
    assert load_local_bundle(tmp_path,training_orders) is not None
    changed=training_orders.copy()
    changed.loc[0,"sales"] += 1
    assert dataset_fingerprint(changed) != dataset_fingerprint(training_orders)
    assert load_local_bundle(tmp_path,changed) is None
    meta=json.loads((tmp_path/"model_evaluation.json").read_text())
    meta["schema_version"]="old"
    (tmp_path/"model_evaluation.json").write_text(json.dumps(meta))
    assert load_local_bundle(tmp_path,training_orders) is None

def test_test_targets_cannot_select_model(training_orders, trained):
    data=training_orders.copy()
    _,_,test,_=temporal_split(data)
    data.loc[data.order_id.isin(test.order_id),"late"] = 1-data.loc[data.order_id.isin(test.order_id),"late"]
    comparison=train_models(data,placement_confirmed=True)
    assert comparison["report"]["selected_model"] == trained["report"]["selected_model"]
    assert comparison["report"]["thresholds"] == trained["report"]["thresholds"]
    for name, metrics in trained["report"]["validation"].items():
        for metric, value in metrics.items():
            actual=comparison["report"]["validation"][name][metric]
            if metric=="confusion_matrix":
                assert actual==value
            else:
                assert actual==pytest.approx(value,abs=1e-12)