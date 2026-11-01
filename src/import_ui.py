"""Upload configuration and explicit delivery mapping, isolated from analytics pages."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import pandas as pd
import streamlit as st
from src.data_loader import read_csv_bytes, suggest_mapping, apply_mapping, FIELDS, MAX_UPLOAD_MB, MAX_ROWS, MAX_COLUMNS, normalize_numeric_columns
from src.validation import prepare_orders, PreparedData
from src.csv_workspace import sensitive_columns

@dataclass
class CSVSelection:
    raw: pd.DataFrame
    prepared: PreparedData | None
    source: str
    token: str
    filename: str

def upload_workspace():
    prior=st.session_state.get("_csv_parsed")
    with st.expander("Your CSV · import or change data", expanded=prior is None):
        st.caption(f"Up to {MAX_UPLOAD_MB} MB · {MAX_ROWS:,} rows · {MAX_COLUMNS} columns · source file preserved")
        uploaded=st.file_uploader("Upload a CSV, TSV or delimited text file",type=["csv","tsv","txt"],
                                  key="dataset_upload",max_upload_size=MAX_UPLOAD_MB)
        a,b,c=st.columns(3)
        encoding=a.selectbox("Text encoding",["auto","utf-8-sig","utf-16","cp1252","latin-1"])
        separator=b.selectbox("Separator",["Auto", "Comma (,)", "Semicolon (;)", "Tab", "Pipe (|)"])
        header=c.checkbox("First row contains column names",value=True)
        repair=st.checkbox("Repair duplicate or blank column names",value=True,
                           help="Renames duplicate/blank headers without changing source values. Actions appear in the import summary.")
        missing_text=st.text_input("Other missing-value markers",value="",max_chars=200,help="Optional comma-separated exact tokens, such as NULL,N/A. Empty by default so a valid category like NA stays intact.")
        missing_markers=tuple(value.strip() for value in missing_text.split(",") if value.strip())
        if uploaded is None:
            st.info("Choose a CSV or select Load sample data in the sidebar.")
            root=Path(__file__).resolve().parents[1]
            x,y=st.columns(2)
            for col,name,label in [(x,"general_example.csv","General CSV example"),(y,"delivery_template.csv","Delivery CSV template")]:
                path=root/"data/examples"/name
                if path.exists():
                    col.download_button(label,path.read_bytes(),name,"text/csv")
            st.stop()
    payload=uploaded.getvalue()
    token=sha256(payload).hexdigest()
    parse_key=(token,encoding,separator,header,repair,missing_markers)
    if prior is None or prior[0]!=parse_key:
        with st.spinner("Reading your file and checking its structure…"):
            delimiter={"Auto":"auto","Comma (,)":",","Semicolon (;)":";","Tab":"\t","Pipe (|)":"|"}[separator]
            raw=read_csv_bytes(payload,encoding,uploaded.name,delimiter,header,repair)
        if missing_markers:
            metadata=dict(raw.attrs["csv_import"])
            raw=raw.mask(raw.isin(missing_markers))
            metadata["actions"]=metadata["actions"]+["Applied explicitly declared missing-value markers: "+", ".join(missing_markers)]
            raw.attrs["csv_import"]=metadata
        st.session_state["_csv_parsed"]=(parse_key,raw)
        st.session_state.pop("_generic_export",None)
        st.session_state.pop("_delivery_exports",None)
        st.session_state.pop("_generic_profile",None)
        st.session_state.pop("uploaded_prepared",None)
    raw=st.session_state["_csv_parsed"][1]
    meta=raw.attrs["csv_import"]
    st.caption(f"Loaded {len(raw):,} rows × {len(raw.columns):,} columns · {len(payload)/1024**2:.2f} MB · encoding {meta['encoding']} · separator {meta['delimiter']}")
    for action in meta["actions"]:
        st.caption(action)
    examples=Path(__file__).resolve().parents[1]/"data/examples"
    example_tokens={sha256(p.read_bytes()).hexdigest() for p in examples.glob("*.csv")}
    default_source="Synthetic learning template supplied with SupplyLens" if token in example_tokens else "User-uploaded CSV; provenance not verified"
    source=st.text_input("Dataset source / provenance",value=default_source,key="source_"+token[:10],max_chars=500)
    mode=st.radio("Analysis workspace",["General data exploration","Delivery analytics"],horizontal=True,key="mode_"+token[:10])
    if mode=="General data exploration":
        return CSVSelection(raw,None,source,token,uploaded.name)
    private_columns=sensitive_columns(raw)
    public_columns=[col for col in raw.columns if col not in private_columns]
    mapping,ambiguous=suggest_mapping(public_columns)
    if ambiguous:
        st.warning("Ambiguous fields need your selection: "+", ".join(ambiguous))
    st.caption("Delivery analytics needs order placement, actual customer arrival or verified duration, a promise, and order status. Carrier handover is not customer arrival.")
    with st.expander("Map delivery fields",expanded="uploaded_prepared" not in st.session_state):
        if private_columns:
            st.caption(f"{len(private_columns)} detected contact, location or credential columns are excluded from mapping.")
        with st.form("mapping_"+token[:10]):
            chosen={}
            options=["(Not mapped)"]+public_columns
            core=["order_id","order_date","delivery_date","promised_date","status","region"]
            columns=st.columns(3)
            for i,field in enumerate(core):
                default=mapping.get(field,"(Not mapped)")
                chosen[field]=columns[i%3].selectbox(field,options,index=options.index(default),key=f"map_{token[:10]}_{field}")
            with st.expander("Optional fields and duration-based datasets"):
                columns=st.columns(3)
                for i,field in enumerate(f for f in FIELDS if f not in core):
                    default=mapping.get(field,"(Not mapped)")
                    chosen[field]=columns[i%3].selectbox(field,options,index=options.index(default),key=f"map_{token[:10]}_{field}")
            a,b,c=st.columns(3)
            date_format=a.selectbox("Date format",["ISO8601","%d/%m/%Y","%m/%d/%Y","%d/%m/%Y %H:%M:%S","%m/%d/%Y %H:%M:%S"])
            grain=b.selectbox("Input row represents",["order","item"])
            financial_grain=c.selectbox("Financial values represent",["item","order"])
            a,b=st.columns(2)
            decimal_mark=a.selectbox("Numeric decimal mark",[".",","])
            thousands_label=b.selectbox("Thousands separator",["None","Comma","Dot","Space"])
            thousands={"None":None,"Comma":",","Dot":".","Space":" "}[thousands_label]
            generate_ids=st.checkbox("When no order ID exists, treat each row as one distinct order and create local row IDs.")
            derive_status=st.checkbox("When status is absent, I confirm a recorded customer arrival means delivered; other rows remain unknown.")
            confirmed=st.checkbox("If mapping durations, I confirm they measure order placement to customer arrival.")
            submitted=st.form_submit_button("Validate and use CSV",type="primary")
    config_key=sha256((token+json.dumps(chosen,sort_keys=True)+date_format+grain+financial_grain+str(generate_ids)+str(derive_status)+str(confirmed)+decimal_mark+str(thousands)).encode()).hexdigest()
    if submitted:
        canonical=apply_mapping(raw,{k:v for k,v in chosen.items() if v!="(Not mapped)"})
        if "order_id" not in canonical and generate_ids:
            if grain!="order":
                raise ValueError("Generated row IDs are only valid for one-row-per-order input.")
            canonical["order_id"]=[f"ROW-{i+1:07d}" for i in range(len(raw))]
        if "status" not in canonical and derive_status:
            if "delivery_date" not in canonical:
                raise ValueError("Map a customer delivery date to derive a delivered/unknown status.")
            canonical["status"]=canonical.delivery_date.notna().map({True:"delivered",False:"unknown"})
        if not {"delivery_date","promised_date"}.issubset(canonical) and not confirmed:
            raise ValueError("Confirm duration semantics or map actual customer-arrival and promised dates.")
        canonical=normalize_numeric_columns(canonical,decimal_mark,thousands)
        with st.spinner("Validating dates, order consistency and eligible delivery outcomes…"):
            prepared=prepare_orders(canonical,date_format,grain,financial_grain)
        st.session_state["uploaded_prepared"]=(config_key,prepared)
    stored=st.session_state.get("uploaded_prepared")
    if not stored or stored[0]!=config_key:
        st.info("Confirm the mappings and choose Validate and use CSV. General data exploration is available without delivery fields.")
        st.stop()
    return CSVSelection(raw,stored[1],source,token,uploaded.name)
