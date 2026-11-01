"""Known answers and adversarial ingestion/aggregation cases."""
from pathlib import Path
from io import BytesIO
import numpy as np
import pandas as pd
import pytest
from src.data_loader import read_csv_bytes, suggest_mapping, apply_mapping
from src.validation import prepare_orders
from src.metrics import kpis, group_performance, wilson_interval
from src.preprocessing import filter_orders
from src.insights import build_insights
from src.reporting import safe_csv, summary_frame, markdown_report, analytical_export

@pytest.fixture
def raw():
    return pd.read_csv(Path(__file__).parent / "hand_check.csv", dtype=str)

@pytest.fixture
def prepared(raw):
    return prepare_orders(raw)

def test_hand_checked_delivery_metrics(prepared):
    m = kpis(prepared.orders)
    assert m["total_orders"] == 6
    assert m["eligible_orders"] == 3
    assert m["excluded_orders"] == 3
    assert m["late_orders"] == 1
    assert m["on_time_rate"] == pytest.approx(2/3)
    assert m["mean_signed_delay"] == pytest.approx(1/3)
    assert m["mean_late_delay"] == 3
    assert m["median_delivery_days"] == 4
    assert m["sales"] == 2100

def test_quality_and_source_immutability(raw, prepared):
    assert len(raw) == 9
    assert raw.order_date.iloc[7] == "01/02/2024"
    assert prepared.quality["exact_duplicates_removed"] == 1
    assert prepared.quality["invalid_record_rows"] == 2
    assert prepared.quality["usable_orders"] == 6

def test_cancelled_and_unknown_not_late(prepared):
    p = prepared.orders.set_index("order_id")
    assert p.loc[["D","E","F"], "late"].isna().all()
    assert not p.loc[["D","E","F"], "eligible"].any()

def test_same_calendar_day_is_on_time(raw):
    raw = raw.iloc[:1].copy()
    raw.loc[0,"delivery_date"] = "2024-01-05 22:30:00"
    assert prepare_orders(raw).orders.late.iloc[0] == 0

def test_explicit_date_format(raw):
    r = raw.iloc[[7]].copy()
    r["delivery_date"] = "05/02/2024"
    r["promised_date"] = "06/02/2024"
    assert len(prepare_orders(r, "%d/%m/%Y").orders) == 1
    assert prepare_orders(r, "%d/%m/%Y").orders.order_date.iloc[0].month == 2

@pytest.mark.parametrize("field,value", [("sales","invalid"),("quantity","-1"),("sales","inf"),
                                        ("promised_date","2023-12-31"),("delivery_date","not-a-date")])
def test_invalid_values_excluded(raw, field, value):
    r = raw.iloc[:1].copy()
    r.loc[0,field] = value
    assert prepare_orders(r).orders.empty

def test_missing_required_columns(raw):
    with pytest.raises(ValueError, match="Map order_id"):
        prepare_orders(raw.drop(columns=["order_id"]))

def test_missing_delivery_columns(raw):
    with pytest.raises(ValueError, match="delivery_date"):
        prepare_orders(raw.drop(columns=["delivery_date","promised_date"]))

def test_item_totals_count_once(raw):
    r = pd.concat([raw.iloc[:1], raw.iloc[:1]], ignore_index=True)
    r["item_id"] = ["1","2"]
    r["sales"] = ["25","75"]
    r["quantity"] = ["1","2"]
    p = prepare_orders(r, grain="item", financial_grain="item")
    assert len(p.orders) == 1
    assert p.orders.sales.iloc[0] == 100
    assert p.orders.quantity.iloc[0] == 3
    assert p.quality["exact_duplicates_removed"] == 0

def test_legitimate_identical_items_keep_distinct_line_ids(raw):
    r = pd.concat([raw.iloc[:1], raw.iloc[:1]], ignore_index=True)
    r["item_id"] = ["1","2"]
    assert prepare_orders(r, grain="item").orders.sales.iloc[0] == 200

def test_item_without_identifier_rejected(raw):
    with pytest.raises(ValueError, match="item_id"):
        prepare_orders(raw, grain="item")

def test_repeated_order_totals_not_doubled(raw):
    r = pd.concat([raw.iloc[:1],raw.iloc[:1]], ignore_index=True)
    r["item_id"] = ["1","2"]
    p = prepare_orders(r, grain="item", financial_grain="order")
    assert p.orders.sales.iloc[0] == 100

def test_conflicting_order_outcomes_excluded(raw):
    r = pd.concat([raw.iloc[:1],raw.iloc[:1]], ignore_index=True)
    r["item_id"] = ["1","2"]
    r.loc[1,"delivery_date"] = "2024-01-09"
    assert prepare_orders(r, grain="item").orders.empty

def test_invalid_line_excludes_siblings(raw):
    r = pd.concat([raw.iloc[:1],raw.iloc[:1]], ignore_index=True)
    r["item_id"] = ["1","2"]
    r.loc[1,"sales"] = "-10"
    assert prepare_orders(r, grain="item").orders.empty

def test_filters_and_zero_denominators(prepared):
    empty = filter_orders(prepared.orders, {"region":["missing"]})
    assert kpis(empty)["on_time_rate"] is None
    assert build_insights(empty) == []
    cancelled = filter_orders(prepared.orders, {"delivery_outcome":["Excluded / unknown"]})
    assert kpis(cancelled)["eligible_orders"] == 0

def test_insights_match_metrics_and_small_groups(prepared):
    orders = prepared.orders
    assert build_insights(orders, minimum=30) == []
    group = group_performance(orders, "region", minimum=30)
    assert group.evidence.eq("Insufficient evidence").all()
    insight = build_insights(orders, minimum=1)[0]
    matching = orders.loc[orders.region.eq(insight["group"])]
    assert insight["late_rate"] == kpis(matching)["late_rate"]

def test_wilson_bounds():
    assert wilson_interval(0,0) == (None,None)
    low, high = wilson_interval(3,10)
    assert 0 <= low < .3 < high <= 1

@pytest.mark.parametrize("payload", [b"", b"a,b\n", b"a,a\n1,2", b"a,b\n1,2,3", b'a,b\n"unfinished,2', b"a,b\n1,\x00"])
def test_bad_csv_rejected(payload):
    with pytest.raises(ValueError):
        read_csv_bytes(payload)

def test_encoding_and_extension():
    with pytest.raises(ValueError, match="Encoding"):
        read_csv_bytes(b"a,b\n1,\xff")
    with pytest.raises(ValueError, match="Only CSV"):
        read_csv_bytes(b"a,b\n1,2",filename="file.exe")

def test_upload_size_limit(monkeypatch):
    import src.data_loader as module
    monkeypatch.setattr(module, "MAX_UPLOAD_MB", 0)
    with pytest.raises(ValueError, match="exceeds"):
        read_csv_bytes(b"a,b\n1,2")

def test_ambiguous_mapping_and_privacy():
    mapping, ambiguous = suggest_mapping(["Order ID", "order_id", "email"])
    assert "order_id" in ambiguous
    assert "order_id" not in mapping
    raw = pd.DataFrame({"Order ID":["1"],"email":["private@example.com"]})
    assert "email" not in apply_mapping(raw, {"order_id":"Order ID"})
    with pytest.raises(ValueError):
        apply_mapping(raw, {"order_id":"Order ID", "region":"Order ID"})

def test_csv_injection_keeps_real_numbers():
    frame = pd.DataFrame({"text":["=SUM(A1)","   +cmd","@X","-text"],"profit":[-2.5,1,2,3]})
    out = safe_csv(frame).decode("utf-8-sig")
    assert "'=SUM(A1)" in out
    assert "'   +cmd" in out
    assert "-2.5" in out and "'-2.5" not in out

def test_exports_agree_with_filtered_metrics(prepared):
    selected = filter_orders(prepared.orders, {"region":["North"]})
    summary = summary_frame(selected, "test fixture, synthetic", {"region":["North"]})
    assert summary.total_orders.iloc[0] == len(selected)
    assert summary.on_time_rate.iloc[0] == kpis(selected)["on_time_rate"]
    assert b"test fixture" in markdown_report(selected, "test fixture", {})
    exported = pd.read_csv(BytesIO(analytical_export(selected, "test fixture", {})))
    assert len(exported) == len(selected)
    assert "report_metric_definitions" in exported

def test_supplied_label_mismatch_flagged(raw):
    r = raw.iloc[:1].copy()
    r["supplied_late"] = "1"
    assert prepare_orders(r).quality["label_mismatches"] == 1
