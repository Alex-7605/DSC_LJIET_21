"""Exercise real import/mapping handlers using Streamlit's app test runner."""
from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

class LocalCSV(BytesIO):
    name="uploaded.csv"

def mock_upload(monkeypatch,payload):
    def upload(*args,**kwargs):
        return LocalCSV(payload) if kwargs.get("key")=="dataset_upload" else None
    monkeypatch.setattr(st,"file_uploader",upload)

def test_general_csv_full_workflow_and_all_charts(monkeypatch):
    mock_upload(monkeypatch,(ROOT/"data/examples/general_example.csv").read_bytes())
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    app.radio(key="data_choice").set_value("Upload CSV").run()
    assert not app.exception
    assert app.metric[0].value=="5"
    for chart in ["Numeric distribution","Group comparison","Scatter plot","Numeric correlations","Time trend","Category counts"]:
        next(s for s in app.selectbox if s.label=="Chart type").set_value(chart).run()
        assert not app.exception,chart
    next(b for b in app.button if b.label=="Prepare data export").click().run()
    assert not app.exception and app.session_state["_generic_export"]
    app.radio(key="page").set_value("Model Evaluation").run()
    assert not app.exception
    assert any("not enabled" in i.value for i in app.info)

def test_delivery_mapping_with_upload(monkeypatch):
    mock_upload(monkeypatch,(ROOT/"data/examples/delivery_template.csv").read_bytes())
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    app.radio(key="data_choice").set_value("Upload CSV").run()
    next(r for r in app.radio if r.label=="Analysis workspace").set_value("Delivery analytics").run()
    next(b for b in app.button if b.label=="Validate and use CSV").click().run()
    assert not app.exception
    assert app.metric[0].value=="3"
    assert next(m for m in app.metric if m.label=="On-time delivery").value=="50.0%"

def test_csv_missing_order_id_and_status_can_be_explicitly_mapped(monkeypatch):
    payload=b"order_date,delivery_date,promised_date\n2024-01-01,2024-01-02,2024-01-03\n"
    mock_upload(monkeypatch,payload)
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    app.radio(key="data_choice").set_value("Upload CSV").run()
    next(r for r in app.radio if r.label=="Analysis workspace").set_value("Delivery analytics").run()
    next(c for c in app.checkbox if c.label.startswith("When no order ID")).check()
    next(c for c in app.checkbox if c.label.startswith("When status")).check()
    next(b for b in app.button if b.label=="Validate and use CSV").click().run()
    assert not app.exception
    assert app.metric[0].value=="1"

def test_reset_demo_filters_and_lazy_reports():
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    next(m for m in app.multiselect if m.label=="Region").set_value(["SP"]).run()
    next(b for b in app.button if b.label=="Reset all filters").click().run()
    assert app.metric[0].value=="12,000"
    next(b for b in app.button if b.label=="Prepare downloads").click().run()
    assert app.session_state["_delivery_exports"]
    next(b for b in app.button if b.label=="Start guided demo").click().run()
    assert app.session_state["demo_active"]
    next(b for b in app.button if b.label=="Next section →").click().run()
    assert app.radio(key="page").value=="Explore Data"
    assert not app.exception

def test_single_text_column_and_ambiguous_dates_remain_usable(monkeypatch):
    mock_upload(monkeypatch,b"odd column\n01/02/2024\nnot a date\n")
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    app.radio(key="data_choice").set_value("Upload CSV").run()
    assert not app.exception
    assert app.metric[0].value=="2"
    assert not any(s.label=="Date column" for s in app.selectbox)

def test_import_error_is_actionable_without_an_exception(monkeypatch):
    mock_upload(monkeypatch,b"a,b\n1,2,3\n")
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    app.radio(key="data_choice").set_value("Upload CSV").run()
    assert not app.exception
    assert app.error and "Malformed CSV" in app.error[0].value

def test_explicit_missing_markers_and_export_invalidation(monkeypatch):
    mock_upload(monkeypatch,b"group,value\nNorth,2\nSouth,NA\n")
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    app.radio(key="data_choice").set_value("Upload CSV").run()
    next(b for b in app.button if b.label=="Prepare data export").click().run()
    assert app.session_state["_generic_export"]
    next(t for t in app.text_input if t.label=="Other missing-value markers").set_value("NA").run()
    assert not app.exception
    assert app.session_state["_generic_profile"][1].numeric_columns==["value"]
    assert "_generic_export" not in app.session_state

def test_private_fields_are_not_available_in_delivery_mapping(monkeypatch):
    payload=b"order_id,order_date,delivery_date,promised_date,status,email,customer_name\na,2024-01-01,2024-01-02,2024-01-03,delivered,private@example.com,Alice\n"
    mock_upload(monkeypatch,payload)
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    app.radio(key="data_choice").set_value("Upload CSV").run()
    next(r for r in app.radio if r.label=="Analysis workspace").set_value("Delivery analytics").run()
    options=next(s for s in app.selectbox if s.label=="region").options
    assert "email" not in options and "customer_name" not in options
    assert not app.exception
