"""CSV dialects, large files, type preservation, privacy and general export contracts."""
from io import BytesIO
import json
import zipfile
import pandas as pd
import pytest
from src.data_loader import read_csv_bytes, suggest_mapping, MAX_UPLOAD_MB
from src.csv_workspace import infer_general, filter_general, general_bundle
from src.reporting import safe_csv, html_report
from src.validation import prepare_orders

@pytest.mark.parametrize("separator",[",",";","\t","|"])
def test_dialects_and_quoted_multiline(separator):
    data=f'label{separator}value\n"first\nsecond"{separator}12\n'
    frame=read_csv_bytes(data.encode(),delimiter=separator)
    assert frame.iloc[0].tolist()==["first\nsecond","12"]

def test_auto_semicolon_and_utf16():
    frame=read_csv_bytes("region;value\nNorth;12\n".encode("utf-16"),encoding="auto")
    assert list(frame)==["region","value"]
    assert frame.attrs["csv_import"]["encoding"]=="utf-16"

def test_windows_encoding_and_literal_na():
    frame=read_csv_bytes("region;value\ncafé;NA\n".encode("cp1252"),encoding="auto")
    assert frame.iloc[0].tolist()==["café","NA"]

def test_one_column_headerless_and_header_repair():
    assert read_csv_bytes(b"one\ntwo\n").iloc[0,0]=="two"
    headerless=read_csv_bytes(b"1,2\n3,4\n",has_header=False)
    assert list(headerless)==["column_1","column_2"]
    assert len(headerless)==2
    repaired=read_csv_bytes(b"a,a,,a_2\n1,2,3,4\n",normalize_headers=True)
    assert len(set(repaired.columns))==4
    assert repaired.attrs["csv_import"]["actions"]

def test_long_quoted_field():
    text="x"*150000
    frame=read_csv_bytes(("notes\n"+text+"\n").encode())
    assert len(frame.iloc[0,0])==150000

def test_file_larger_than_previous_limit():
    payload=b"measurement,description\n"+(b"1,"+b"x"*510+b"\n")*55000
    assert len(payload)>25*1024*1024
    assert MAX_UPLOAD_MB>=200
    assert len(read_csv_bytes(payload))==55000

def test_row_and_column_caps(monkeypatch):
    import src.data_loader as loader
    monkeypatch.setattr(loader,"MAX_ROWS",1)
    with pytest.raises(ValueError,match="Maximum"):
        loader.read_csv_bytes(b"a,b\n1,2\n3,4\n")
    monkeypatch.setattr(loader,"MAX_COLUMNS",1)
    with pytest.raises(ValueError,match="columns"):
        loader.read_csv_bytes(b"a,b\n1,2\n")

def test_normalized_aliases_preserve_ambiguity():
    mapping,ambiguous=suggest_mapping(["ORDER-ID","Order Date","actual_delivery_date","expected_delivery_date"])
    assert mapping["order_id"]=="ORDER-ID"
    assert mapping["delivery_date"]=="actual_delivery_date"
    mapping,ambiguous=suggest_mapping(["ORDER ID","order_id"])
    assert "order_id" in ambiguous and "order_id" not in mapping

def test_general_inference_never_fakes_delivery_and_preserves_codes():
    raw=read_csv_bytes(b"code,amount,ambiguous_date,mixed\n001,2.5,01/02/2024,10\n002,3.5,02/03/2024,error\n")
    dataset=infer_general(raw)
    assert dataset.numeric_columns==["amount"]
    assert dataset.frame.code.iloc[0]=="001"
    assert not dataset.date_columns
    assert "late" not in dataset.frame

def test_decimal_comma_duplicates_and_source_preservation():
    raw=read_csv_bytes(b"group;amount\nA;1,25\nA;1,25\n")
    assert len(infer_general(raw,decimal=",").frame)==2
    cleaned=infer_general(raw,decimal=",",remove_duplicates=True)
    assert cleaned.frame.amount.iloc[0]==1.25 and len(cleaned.frame)==1
    assert raw.amount.iloc[0]=="1,25" and len(raw)==2

def test_sensitive_columns_excluded_even_beyond_preview():
    raw=pd.DataFrame({"name":["A"]*2100,"notes":["ok"]*2099+["secret@example.com"],"value":["1"]*2100})
    dataset=infer_general(raw)
    assert set(dataset.hidden_columns)=={"name","notes"}
    assert list(dataset.frame)==["value"]

def test_general_filters_and_zip_context():
    raw=read_csv_bytes(b"group,value\nNorth,2\nSouth,8\nNorth,10\n")
    dataset=infer_general(raw)
    selected=filter_general(dataset.frame,search="north",search_columns=["group"],numeric={"value":(3,12)})
    assert len(selected)==1 and selected.value.iloc[0]==10
    archive=general_bundle(selected,dataset,"test fixture",{"region":"North"})
    with zipfile.ZipFile(BytesIO(archive)) as z:
        assert len(pd.read_csv(z.open("selected_data.csv")))==1
        context=json.loads(z.read("report_context.json"))
        assert context["exported_rows"]==1
        assert "not assumed" in context["analytical_unit"]

def test_formula_headers_are_sanitized_without_corrupting_numbers():
    out=safe_csv(pd.DataFrame({"=CMD()":["=BAD()"],"profit":[-2.5]})).decode("utf-8-sig")
    assert "'=CMD()" in out and "'=BAD()" in out
    assert "'-2.5" not in out

def test_print_report_escapes_user_text():
    raw=read_csv_bytes(b"order_id,order_date,delivery_date,promised_date,status,region\na,2024-01-01,2024-01-04,2024-01-03,delivered,X\n")
    orders=prepare_orders(raw).orders
    report=html_report(orders,"<script>alert(1)</script>",{},minimum=1).decode()
    assert "<script>" not in report and "&lt;script&gt;" in report
    assert "Delivery performance report" in report

def test_delivery_numeric_conventions_are_explicit():
    from src.data_loader import normalize_numeric_columns
    raw=pd.DataFrame({"order_id":["001"],"sales":["1.234,50"],"quantity":["2"]})
    normalized=normalize_numeric_columns(raw,decimal=",",thousands=".")
    assert normalized.sales.iloc[0]=="1234.50"
    assert normalized.order_id.iloc[0]=="001"
    assert raw.sales.iloc[0]=="1.234,50"
    with pytest.raises(ValueError,match="different"):
        normalize_numeric_columns(raw,decimal=",",thousands=",")

def test_duplicate_removal_uses_original_source_not_hidden_values():
    raw=pd.DataFrame({"name":["Alice","Bob"],"value":["1","1"]})
    dataset=infer_general(raw,remove_duplicates=True)
    assert len(dataset.frame)==2
    assert list(dataset.frame)==["value"]

def test_launcher_preserves_occupied_ports():
    import socket
    from scripts.launch import available_port
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1",0))
        busy=reserved.getsockname()[1]
        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1",0))
            free=candidate.getsockname()[1]
        assert available_port([busy,free])==free
        with pytest.raises(RuntimeError):
            available_port([busy])
