"""Shared visual language and presentation controls."""
from html import escape
import streamlit as st

PAGES = ["Overview", "Explore Data", "Delivery Performance", "Business Insights",
         "Predict Delivery Risk", "Model Evaluation", "Project Guide"]
TIPS = {
    "Overview": "Start with the population: total orders and eligible delivered orders have different meanings.",
    "Explore Data": "Show the data-quality checks before explaining a chart.",
    "Delivery Performance": "Compare late rates alongside order volume and the size of each group.",
    "Business Insights": "Read the evidence, baseline, suggested investigation and limitation together.",
    "Predict Delivery Risk": "The inputs must be available at order placement. A probability is an estimate.",
    "Model Evaluation": "Compare late precision and recall with the dummy. Explain weak results honestly.",
    "Project Guide": "Finish with the data flow, limitations and a realistic future improvement.",
}

def inject_theme():
    st.markdown("""
<style>
.stApp {background:#F5F7FB;}
html,body,.stApp,[data-testid="stMarkdownContainer"] {font-family:"Segoe UI",Arial,sans-serif;}
h1,h2,h3 {color:#16324F;letter-spacing:-.035em;font-weight:750;}
h1 {font-size:2.15rem!important;}
h2 {font-size:1.45rem!important;}
h3 {font-size:1.12rem!important;}
.block-container {max-width:1500px;padding:3.7rem 3rem 2.4rem;}
[data-testid="stSidebar"] {background:#16324F;border-right:0;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label,[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] summary {color:#E9F0F6!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:.35rem .6rem;border-radius:8px;min-height:39px;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {background:#24506B;color:white!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:#20445E;}
[data-testid="stSidebar"] button {border-color:#BBCBD7;}
[data-testid="stSidebar"] button [data-testid="stMarkdownContainer"] {color:#16324F!important;}
[data-testid="stSidebar"] button[kind="primary"] [data-testid="stMarkdownContainer"] {color:white!important;}
[data-testid="stSidebar"] [data-testid="stExpander"] details,
[data-testid="stSidebar"] [data-testid="stExpander"] summary {background:#1B3D58!important;color:#E9F0F6!important;}
[data-testid="stSidebar"] [data-testid="stExpander"] {background:#1B3D58;border:1px solid #35536B;}
[data-testid="stSidebar"] hr {border-color:#35536B;}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {color:#D6E5EE!important;}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#16324F;}
[data-testid="stSidebar"] [data-testid="stNumberInput"] input {color:#16324F;}
.brand {display:flex;gap:12px;align-items:center;padding:8px 0 23px;color:white;}
.brandmark {display:grid;place-items:center;width:43px;height:43px;border-radius:12px;background:#147D92;font-size:25px;font-weight:800;}
.brand strong {display:block;font-size:1.4rem;letter-spacing:-.04em;}
.brand small {font-size:.69rem;letter-spacing:.12em;color:#B8D4E0;}
.eyebrow {font-size:.72rem;letter-spacing:.14em;font-weight:800;color:#147D92;margin-bottom:10px;}
.hero {display:flex;justify-content:space-between;gap:24px;padding:0 0 12px;border-bottom:1px solid #DEE7EF;margin-bottom:14px;}
.hero h1 {margin:0;padding:0 0 9px;line-height:1.13;}
.hero p {margin:0;color:#64748B;font-size:.96rem;max-width:660px;line-height:1.6;}
.hero-tag {align-self:center;white-space:nowrap;border:1px solid #CFDFE8;border-radius:999px;padding:8px 13px;font-size:.74rem;background:#FFF;color:#147D92;font-weight:700;}
.context-strip {display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:2px 0 15px;font-size:.75rem;color:#64748B;}
.context-strip span {background:#FFF;border:1px solid #E0E7EF;border-radius:7px;padding:6px 10px;}
[data-testid="stMetric"] {background:white;border:1px solid #DFE7EF;border-radius:13px;padding:17px 19px;box-shadow:0 2px 3px #16324F03;}
[data-testid="stMetricLabel"] {color:#64748B;font-size:.8rem;}
[data-testid="stMetricValue"] {color:#16324F;font-weight:800;font-size:clamp(1.4rem,2.35vw,2.05rem);}
[data-testid="stPlotlyChart"] {background:white;border:1px solid #E0E7EF;border-radius:13px;padding:4px;}
[data-testid="stExpander"] {background:white;border:1px solid #E0E7EF;border-radius:11px;}
[data-testid="stDataFrame"] {border-radius:10px;}
[data-testid="stTabs"] [role="tablist"] {gap:18px;border-bottom:1px solid #DFE7EF;}
[data-testid="stTabs"] [role="tab"] {font-weight:650;}
[data-testid="stForm"] {background:#FFF;border:1px solid #DFE7EF;border-radius:13px;}
[data-testid="stDownloadButton"] button {background:#FFF;}
.section-note {background:#E8F3F5;color:#16324F;border-left:3px solid #147D92;padding:13px 16px;border-radius:0 9px 9px 0;font-size:.85rem;line-height:1.6;margin:8px 0 16px;}
.footer-note {color:#64748B;font-size:.72rem;border-top:1px solid #DFE7EF;padding-top:16px;margin-top:22px;}
@media(max-width:1200px) {
.block-container {padding-left:1.8rem;padding-right:1.8rem;}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {flex-wrap:wrap;}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"] {flex:1 1 calc(50% - 1rem)!important;width:calc(50% - 1rem)!important;min-width:0!important;}
[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) {flex-wrap:wrap;}
[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) > [data-testid="stColumn"] {flex:1 1 100%!important;width:100%!important;min-width:0!important;}
}
@media(max-width:700px) {
.block-container {padding:4rem 1rem 1.5rem;}
.hero {display:block;}.hero-tag {display:none;}h1 {font-size:1.8rem!important;}
}
@media print {
[data-testid="stSidebar"],header,[data-testid="stToolbar"],[data-testid="stDownloadButton"] {display:none!important;}
.block-container {padding:0;max-width:100%;}
}
</style>
""", unsafe_allow_html=True)

def header(title, subtitle, tag="DELIVERY INTELLIGENCE"):
    st.markdown(f'<div class="eyebrow">SUPPLY CHAIN PERFORMANCE & DELIVERY EFFICIENCY</div>'
                f'<div class="hero"><div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>'
                f'<div class="hero-tag">{escape(tag)}</div></div>', unsafe_allow_html=True)

def context_strip(parts):
    st.markdown('<div class="context-strip">' + "".join(f"<span>{escape(str(p))}</span>" for p in parts) + "</div>", unsafe_allow_html=True)

def clear_filters(fingerprint):
    for key in list(st.session_state):
        if key.endswith("_"+fingerprint[:8]) or key=="date_"+fingerprint[:8]:
            del st.session_state[key]

def start_demo():
    st.session_state["data_choice"]="Load sample data"
    st.session_state["page"]="Overview"
    st.session_state["demo_active"]=True
    for key in list(st.session_state):
        if key.startswith(("region_","category_","shipping_mode_","segment_","delivery_outcome_","date_","order_search_")):
            del st.session_state[key]

def next_demo():
    index=PAGES.index(st.session_state.get("page","Overview"))
    if index==len(PAGES)-1:
        st.session_state["demo_active"]=False
    else:
        st.session_state["page"]=PAGES[index+1]

def demo_controls(page):
    if st.session_state.get("demo_active"):
        index=PAGES.index(page)
        with st.container(border=True):
            st.caption(f"GUIDED DEMO · {index+1} / {len(PAGES)}")
            st.write(TIPS[page])
            st.progress((index+1)/len(PAGES))
            st.button("Finish tour" if index==len(PAGES)-1 else "Next section →", on_click=next_demo, key="next_demo")
