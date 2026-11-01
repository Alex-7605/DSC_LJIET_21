"""Small display and filter helpers."""
import streamlit as st

PAGES = ["Overview", "Explore Data", "Delivery Performance", "Business Insights",
         "Predict Delivery Risk", "Model Evaluation"]

def inject_theme():
    st.markdown("""
<style>
.stApp {background:white;}
[data-testid="stSidebar"] {background:#F1F3F5;}
.block-container {max-width:1300px;padding-top:3.5rem;}
h1 {font-size:1.9rem!important;}
h2 {font-size:1.4rem!important;}
[data-testid="stMetricValue"] {font-size:1.8rem;}
@media(max-width:1100px) {
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {flex-wrap:wrap;}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"] {flex:1 1 calc(50% - 1rem)!important;width:calc(50% - 1rem)!important;min-width:0!important;}
[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) {flex-wrap:wrap;}
[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) > [data-testid="stColumn"] {flex:1 1 100%!important;width:100%!important;min-width:0!important;}
}
</style>
""",unsafe_allow_html=True)

def header(title, subtitle="", tag=""):
    st.title(title)

def context_strip(parts):
    st.caption(" | ".join(str(part) for part in parts))

def clear_filters(fingerprint):
    for key in list(st.session_state):
        if key.endswith("_"+fingerprint[:8]) or key=="date_"+fingerprint[:8]:
            del st.session_state[key]
