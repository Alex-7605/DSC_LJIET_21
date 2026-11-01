"""Supply Chain Performance and Delivery Efficiency Analysis — local college project."""
from pathlib import Path
import json
import hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.data_loader import read_csv_bytes, suggest_mapping, apply_mapping, FIELDS, MAX_UPLOAD_MB
from src.validation import prepare_orders
from src.preprocessing import filter_orders
from src.metrics import kpis, group_performance, DEFINITIONS
from src.insights import build_insights
from src.modeling import train_models, predict_batch, load_local_bundle, dataset_fingerprint, feature_audit, NUMERIC
from src.reporting import analytical_export, summary_frame, safe_csv, markdown_report, evaluation_export, LIMITATIONS
from src.visualizations import style, outcome_chart, group_chart, trend_chart, distribution, correlation_chart

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Supply Chain | Delivery Intelligence", page_icon="📦", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"], .stApp {font-family:Arial,sans-serif;}
h1,h2,h3 {color:#16324F; letter-spacing:-.035em;}
.block-container {max-width:1450px; padding-top:4rem; padding-bottom:3rem;}
[data-testid="stSidebar"] {background:#FFF; border-right:1px solid #E1E8F0;}
[data-testid="stMetric"] {background:#FFF; border:1px solid #E1E8F0; border-radius:14px; padding:20px 22px;}
[data-testid="stMetricLabel"] {color:#64748B; font-size:.85rem;}
[data-testid="stMetricValue"] {color:#16324F; font-weight:800; font-size:clamp(1.4rem,2.6vw,2.2rem);}
[data-testid="stPlotlyChart"] {background:white; border:1px solid #E1E8F0; border-radius:14px; padding:4px;}
[data-testid="stExpander"] {background:white; border:1px solid #E1E8F0; border-radius:12px;}
.eyebrow {color:#147D92; font-size:.77rem; font-weight:700; letter-spacing:.17em; text-transform:uppercase; margin-bottom:12px;}
.brand {color:#16324F; font-size:1.45rem; font-weight:800; line-height:1.2;}
.brand small {color:#64748B; font-size:.7rem; font-weight:500; letter-spacing:.12em;}
.hero {padding:20px 0 16px;}
.hero h1 {font-size:2.65rem; line-height:1.15; margin:0 0 10px;}
.hero p {color:#64748B; font-size:1rem;}
.rule {height:4px; width:42px; background:#147D92; border-radius:3px; margin:16px 0 20px;}
[data-testid="stDownloadButton"] button {background:white;}
@media(max-width:1200px) {
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {flex-wrap:wrap;}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"] {flex:1 1 calc(50% - 1rem)!important; width:calc(50% - 1rem)!important; min-width:0!important;}
[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) {flex-wrap:wrap;}
[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) > [data-testid="stColumn"] {flex:1 1 100%!important; width:100%!important; min-width:0!important;}
}
@media(max-width:800px) {.hero h1 {font-size:1.9rem;} .block-container {padding:4rem 1rem 1rem;}}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def sample_data():
    return prepare_orders(pd.read_csv(ROOT / "data/sample/olist_orders_sample.csv", dtype=str))

def number(value, suffix="", percentage=False):
    if value is None or pd.isna(value):
        return "Not available"
    return f"{value:.1%}" if percentage else f"{value:,.1f}{suffix}"

with st.sidebar:
    st.markdown('<div class="brand">◈ Supply Chain<br><small>PERFORMANCE & DELIVERY</small></div><div class="rule"></div>', unsafe_allow_html=True)
    page = st.radio("Workspace", ["Overview", "Explore Data", "Delivery Performance", "Business Insights",
                                 "Predict Delivery Risk", "Model Evaluation", "Project Guide"], key="page")
    st.divider()
    data_choice = st.radio("Dataset", ["Load sample data", "Upload CSV"], key="data_choice")
    minimum = st.number_input("Minimum group size", min_value=5, max_value=500, value=30, step=5,
                              help="Smaller groups remain visible but are excluded from ranked insights.")

provenance = json.loads((ROOT / "data/sample/provenance.json").read_text(encoding="utf-8"))
if data_choice == "Load sample data":
    prepared = sample_data()
    source = provenance["source_url"] + " | Real Olist 12,000-order sample"
    dataset_name = "Olist · 12,000 real orders"
    is_sample = True
else:
    st.subheader("Bring your order data")
    st.caption(f"CSV only · up to {MAX_UPLOAD_MB} MB and 250,000 rows · kept in your local session. Unknown columns are discarded.")
    uploaded = st.file_uploader("Upload order or order-item CSV", type=["csv"])
    if uploaded is None:
        st.info("Choose a CSV or select Load sample data in the sidebar.")
        st.stop()
    encoding = st.selectbox("File encoding", ["utf-8-sig", "cp1252", "latin-1"])
    try:
        raw = read_csv_bytes(uploaded.getvalue(), encoding, uploaded.name)
    except ValueError as error:
        st.error(str(error))
        st.stop()
    st.write("Detected columns")
    st.dataframe(pd.DataFrame({"Source column": raw.columns}), hide_index=True, width="stretch")
    mapping, ambiguous = suggest_mapping(raw.columns)
    if ambiguous:
        st.warning("Choose mappings for ambiguous fields: " + ", ".join(ambiguous))
    with st.form("mapping"):
        st.caption("Map only non-identifying business fields. Do not map names, emails, street addresses or phone numbers. Delivery date means customer arrival, never carrier handover.")
        columns = st.columns(3)
        chosen = {}
        options = ["(Not mapped)"] + list(raw.columns)
        for i, field in enumerate(FIELDS):
            default = mapping.get(field, "(Not mapped)")
            chosen[field] = columns[i % 3].selectbox(field, options, index=options.index(default), key="map_" + field)
        date_format = st.selectbox("Date format (explicit)", ["ISO8601", "%d/%m/%Y", "%m/%d/%Y", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"])
        grain = st.selectbox("Input row represents", ["order", "item"])
        financial_grain = st.selectbox("Financial values represent", ["item", "order"],
                                        help="Item: sum line values. Order: repeated totals must agree and are counted once.")
        source_note = st.text_input("Dataset source / provenance", value="User-uploaded CSV; provenance not verified")
        durations_confirmed = st.checkbox("If using durations instead of dates: these measure order placement to customer delivery.")
        validate_clicked = st.form_submit_button("Validate and use CSV", type="primary")
    config_key = hashlib.sha256((str(chosen)+date_format+grain+financial_grain+source_note+str(durations_confirmed)).encode()+uploaded.getvalue()).hexdigest()
    if validate_clicked:
        try:
            canonical = apply_mapping(raw, {k: v for k, v in chosen.items() if v != "(Not mapped)"})
            if not {"delivery_date", "promised_date"}.issubset(canonical) and not durations_confirmed:
                raise ValueError("Confirm duration semantics, or map actual customer-delivery and promised dates.")
            result = prepare_orders(canonical, date_format, grain, financial_grain)
            st.session_state["uploaded_prepared"] = (config_key, result)
        except ValueError as error:
            st.error(str(error))
            st.stop()
    stored = st.session_state.get("uploaded_prepared")
    if not stored or stored[0] != config_key:
        st.info("Confirm the mapping and select Validate and use CSV.")
        st.stop()
    prepared = stored[1]
    source = source_note
    dataset_name = "Uploaded data · provenance unverified"
    is_sample = False

orders = prepared.orders
fingerprint = dataset_fingerprint(orders)
if st.session_state.get("active_fingerprint") != fingerprint:
    st.session_state["active_fingerprint"] = fingerprint
    st.session_state["bundle"] = None
    if is_sample:
        try:
            st.session_state["bundle"] = load_local_bundle(ROOT / "artifacts", orders)
        except (OSError, ValueError, KeyError):
            st.session_state["bundle"] = None

with st.sidebar:
    st.caption(dataset_name)
    if not orders.empty:
        st.caption(f"Coverage: {orders.order_date.min():%d %b %Y} — {orders.order_date.max():%d %b %Y}")
    with st.expander("Filter orders", expanded=False):
        filters = {}
        if not orders.empty:
            coverage = st.date_input("Order date range", value=(orders.order_date.min().date(), orders.order_date.max().date()),
                                     min_value=orders.order_date.min().date(), max_value=orders.order_date.max().date(), key="date_" + fingerprint[:8])
            if len(coverage) == 2:
                filters.update(start=str(coverage[0]), end=str(coverage[1]))
        for col in ["region", "shipping_mode", "category", "segment", "delivery_outcome"]:
            if col in orders:
                filters[col] = st.multiselect(col.replace("_", " ").title(), sorted(orders[col].dropna().unique()), key=f"{col}_{fingerprint[:8]}")
    st.caption("Empty category selections mean all values. Filters affect descriptive analysis and exports.")
    st.caption("Local application · single user · no external prediction API")

filtered = filter_orders(orders, filters)
metrics = kpis(filtered)
active = [f"{key}: {', '.join(value) if isinstance(value, list) else value}" for key, value in filters.items() if value]
st.markdown('<div class="eyebrow">SUPPLY CHAIN INTELLIGENCE / COLLEGE DATA SCIENCE PROJECT</div>', unsafe_allow_html=True)
if page == "Overview":
    st.markdown('<div class="hero"><h1>Every order tells<br>a delivery story.</h1><p>Understand delivery performance. Find patterns. Investigate with evidence.</p></div>', unsafe_allow_html=True)
else:
    st.title(page)
st.caption(f"{dataset_name}  •  Analytical unit: distinct order  •  {len(filtered):,} selected orders")
st.caption("Active filters — " + (" | ".join(active) if active else "All orders"))
if is_sample:
    st.caption("Source: Olist / Kaggle · adapted real data · CC BY-NC-SA 4.0 · historical sample, 2016–2018")
if prepared.quality["label_mismatches"]:
    st.warning(f"{prepared.quality['label_mismatches']} supplied labels disagree with derived late flags. Inspect source definitions; modeling is blocked.")

if page in ["Overview", "Explore Data", "Delivery Performance", "Business Insights"] and filtered.empty:
    st.info("No orders match the current filters. Clear a category or widen the date range.")
elif page == "Overview":
    columns = st.columns(4)
    columns[0].metric("Selected orders", f"{metrics['total_orders']:,}", help="One record per distinct order after validation.")
    columns[1].metric("On-time delivery", number(metrics["on_time_rate"], percentage=True), help="On-time / eligible delivered orders.")
    columns[2].metric("Late deliveries", f"{metrics['late_orders']:,}", help=f"Of {metrics['eligible_orders']:,} eligible delivered orders.")
    columns[3].metric("Median delivery", number(metrics["median_delivery_days"], " days"), help="Order placement to customer delivery; calendar days.")
    st.caption(f"Denominator: {metrics['eligible_orders']:,} eligible delivered orders · {metrics['excluded_orders']:,} cancelled, undelivered or unknown-outcome orders excluded.")
    left, right = st.columns([.85, 1.4])
    with left:
        st.plotly_chart(outcome_chart(filtered), width="stretch")
    with right:
        dimension = "region" if "region" in filtered else "status"
        chart, _ = group_chart(filtered, dimension, minimum)
        st.plotly_chart(chart, width="stretch")
        st.caption("Top 10 groups by eligible volume. Rates use each group's eligible orders. Rate axis is always 0–100%.")
    st.plotly_chart(trend_chart(filtered), width="stretch")
    insights = build_insights(filtered, minimum, 1)
    with st.container(border=True):
        st.subheader("An investigation worth starting")
        if insights:
            st.write(insights[0]["finding"])
            st.write(insights[0]["evidence"])
            st.caption(insights[0]["action"])
        else:
            st.write("There is not enough stable group evidence for an above-baseline finding.")
elif page == "Explore Data":
    st.subheader("Data quality before conclusions")
    q = prepared.quality
    a, b, c, d = st.columns(4)
    a.metric("Rows loaded", f"{q['rows_loaded']:,}")
    b.metric("Usable orders", f"{q['usable_orders']:,}")
    c.metric("Exact duplicates", f"{q['exact_duplicates_removed']:,}")
    d.metric("Invalid record rows", f"{q['invalid_record_rows']:,}")
    st.json({k: v for k, v in q.items() if k not in {"missing_values", "actions"}})
    st.dataframe(pd.DataFrame(list(q["missing_values"].items()), columns=["Field", "Missing source values"]), hide_index=True)
    for action in q["actions"]:
        st.write("• " + action)
    st.caption("Quality totals cover the full submitted dataset; the analytical preview and exports follow filters.")
    st.subheader("Analytical preview")
    st.dataframe(filtered.head(200), hide_index=True, width="stretch")
    with st.expander("Exclusion reasons (full dataset)"):
        st.dataframe(prepared.exclusions.groupby("reason").size().reset_index(name="Records"), hide_index=True)
elif page == "Delivery Performance":
    a, b, c = st.columns(3)
    a.metric("Mean signed delay", number(metrics["mean_signed_delay"], " days"))
    b.metric("Mean late-only delay", number(metrics["mean_late_delay"], " days"))
    c.metric("Eligible orders", f"{metrics['eligible_orders']:,}")
    st.caption("A negative signed delay means early arrival. Late-only mean includes positive delays only.")
    dimension = st.selectbox("Compare delivery groups", [c for c in ["region", "category", "shipping_mode", "segment", "status"] if c in filtered])
    chart, table = group_chart(filtered, dimension, minimum)
    st.plotly_chart(chart, width="stretch")
    st.caption("Top 10 ranked by eligible volume; all groups including insufficient-evidence groups appear below. Wilson intervals describe rate uncertainty.")
    st.dataframe(group_performance(filtered, dimension, minimum), hide_index=True, width="stretch")
    left, right = st.columns(2)
    left.plotly_chart(distribution(filtered, "actual_days", "Order-to-delivery duration"), width="stretch")
    right.plotly_chart(distribution(filtered, "delay_days", "Signed delay relative to promise"), width="stretch")
    st.plotly_chart(trend_chart(filtered), width="stretch")
elif page == "Business Insights":
    st.caption(f"Groups need at least {minimum} eligible orders for ranked findings.")
    insights = build_insights(filtered, minimum)
    if not insights:
        st.info("No above-baseline group has sufficient evidence for a ranked finding.")
    for rank, item in enumerate(insights, 1):
        with st.container(border=True):
            st.subheader(f"{rank:02d} · {item['finding']}")
            st.write(item["evidence"])
            st.write(item["baseline"])
            st.caption(item["uncertainty"])
            st.write("Action to consider: " + item["action"])
            st.caption("Limitation: " + item["limitation"])
    with st.expander("How investigation priority is calculated"):
        st.write("Priority = late-order count × max(group late rate − overall late rate, 0) × (1 + mean late-only delay / 7).")
        st.caption("Weights are heuristic. Groups overlap across dimensions; scores must not be summed. No statistical significance or causal benefit is claimed.")
    if "sales" in filtered:
        st.subheader("Order value and delivery outcome")
        st.caption("Sales means item-price total excluding freight. Units follow the source; incomplete financial values are not imputed.")
        financials = filtered.loc[filtered.eligible].groupby("delivery_outcome").agg(orders=("order_id", "size"), known_sales=("sales", "count"), sales=("sales", lambda s: s.sum(min_count=1)), mean_order_value=("sales", "mean")).reset_index()
        st.dataframe(financials, hide_index=True, width="stretch")
    fig = correlation_chart(filtered)
    if fig:
        st.plotly_chart(fig, width="stretch")
        st.caption("Eligible orders; pairwise complete values. IDs and encoded categories excluded. Delay is mathematically related to durations. Correlation does not establish causation.")
elif page in ["Predict Delivery Risk", "Model Evaluation"]:
    st.info("Prediction moment: order placement. Evaluation uses the full validated dataset's fixed chronological holdout; dashboard filters do not change training or scores.")
    bundle = st.session_state.get("bundle")
    confirmed = st.checkbox("I confirm these candidate features are available at order placement.", value=is_sample, key="placement_" + fingerprint[:8])
    with st.expander("Feature audit and training workflow", expanded=bundle is None):
        st.dataframe(feature_audit(orders), hide_index=True, width="stretch")
        st.caption("Compare Dummy, Logistic Regression and a modest Random Forest. Preprocessing fits training data only. Model and threshold selection use validation data.")
        if st.button("Train and evaluate models", type="primary", disabled=not confirmed):
            try:
                with st.spinner("Training three models and checking the chronological holdout…"):
                    bundle = train_models(orders, placement_confirmed=confirmed)
                st.session_state["bundle"] = bundle
                st.success("Training completed. Results below use the untouched final test period.")
            except ValueError as error:
                st.error(str(error))
    if bundle:
        report = bundle["report"]
        st.caption(f"Selected model: {report['selected_model']} · threshold {report['threshold']:.2f} · dataset fingerprint {fingerprint[:12]}")
        selected_scores = report["test"][report["selected_model"]]
        dummy_scores = report["test"]["Dummy baseline"]
        if selected_scores["brier_score"] > dummy_scores["brier_score"]:
            st.warning("Limited predictive performance: the selected model has worse held-out probability error than the dummy baseline. Review precision, false alarms and reliability before interpreting a risk estimate.")
        if page == "Predict Delivery Risk":
            st.subheader("Estimate a new order's delivery risk")
            st.caption("All fields are mandatory. Estimates are conditional on eventual observed delivery and may be unreliable outside the training population.")
            with st.form("predict"):
                values = {}
                cols = st.columns(3)
                for i, feature in enumerate(report["features"]):
                    col = cols[i % 3]
                    label = feature.replace("_", " ").title()
                    if feature in NUMERIC:
                        lower, upper = report["training_bounds"][feature]
                        default = float(orders[feature].dropna().median())
                        minimum_value = 1.0 if feature in {"quantity", "order_month"} else 0.0
                        maximum_value = 12.0 if feature == "order_month" else (6.0 if feature == "order_weekday" else (1.0 if feature == "discount" else None))
                        values[feature] = col.number_input(label, min_value=minimum_value, max_value=maximum_value, value=max(minimum_value, default),
                                                          step=1.0 if feature != "discount" else .01,
                                                          help=f"Training range: {lower:g} to {upper:g}. Weekday: Monday=0.")
                    else:
                        values[feature] = col.selectbox(label, report["training_categories"][feature])
                submitted = st.form_submit_button("Estimate delivery risk", type="primary")
            if submitted:
                try:
                    prediction = predict_batch(bundle, pd.DataFrame([values])).iloc[0]
                    a, b, c = st.columns(3)
                    a.metric("Estimated late risk", f"{prediction.late_risk:.1%}")
                    b.metric("Predicted class", prediction.predicted_class)
                    c.metric("Threshold", f"{prediction.threshold:.2f}")
                    st.caption(f"Historical full-dataset late rate: {kpis(orders)['late_rate']:.1%}. This broad reference is not a matched comparison.")
                    if prediction.warnings:
                        st.warning(prediction.warnings)
                    st.info("A model estimate is not guaranteed confidence. Changing a field does not prove improvement; historical associations may reflect different order mixes.")
                except ValueError as error:
                    st.error(str(error))
            st.subheader("Batch predictions")
            template = pd.DataFrame({f: [orders[f].dropna().iloc[0]] for f in report["features"]})
            st.download_button("Download input template", safe_csv(template), "prediction_template.csv", "text/csv")
            batch = st.file_uploader("Prediction inputs CSV (UTF-8)", type=["csv"], key="batch")
            if batch:
                try:
                    frame = read_csv_bytes(batch.getvalue(), filename=batch.name)
                    if len(frame) > 10000:
                        raise ValueError("Batch predictions are limited to 10,000 rows.")
                    predictions = predict_batch(bundle, frame)
                    st.dataframe(predictions, hide_index=True, width="stretch")
                    for key, value in summary_frame(orders, source, {"scope": "Batch inference; model full-dataset holdout"}).iloc[0].items():
                        predictions["report_" + key] = value
                    st.download_button("Download batch predictions", safe_csv(predictions), "batch_predictions.csv", "text/csv")
                    st.caption("submitted_row matches the 1-based input row order. Additional uploaded columns are ignored and never exported.")
                except ValueError as error:
                    st.error(str(error))
        else:
            st.subheader("Measured performance on future orders")
            comparisons = pd.DataFrame(report["test"]).T.drop(columns=["confusion_matrix"])
            comparisons["threshold"] = pd.Series(report["thresholds"])
            st.dataframe(comparisons, width="stretch")
            st.caption("Positive class = late. PR-AUC is average precision (AP). Higher is better except Brier score. Accuracy alone can hide missed late orders.")
            selected = report["test"][report["selected_model"]]
            left, right = st.columns(2)
            with left:
                matrix = px.imshow(selected["confusion_matrix"], x=["Predicted on time", "Predicted late"],
                                   y=["Actual on time", "Actual late"], text_auto=True, color_continuous_scale="Blues")
                st.plotly_chart(style(matrix, "Selected model · confusion matrix"), width="stretch")
            with right:
                cal = report["calibration"]
                fig = go.Figure()
                fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Ideal", line=dict(dash="dash", color="#64748B"))
                fig.add_scatter(x=cal["mean_predicted"], y=cal["observed_late_fraction"], mode="lines+markers", name="Test bins")
                style(fig, "Probability reliability · six quantile bins")
                fig.update_xaxes(range=[0, 1], title="Mean estimated risk")
                fig.update_yaxes(range=[0, 1], title="Observed late fraction")
                st.plotly_chart(fig, width="stretch")
            st.caption(report["calibration"]["note"])
            with st.expander("Split periods, class distribution and purged orders", expanded=True):
                st.json(report["split"])
            with st.expander("Validation results and model selection"):
                st.write(report["selection"])
                st.dataframe(pd.DataFrame(report["validation"]).T.drop(columns=["confusion_matrix"]), width="stretch")
            st.subheader("What the Logistic Regression comparator associates with risk")
            st.dataframe(pd.DataFrame(report["logistic_coefficients"]), hide_index=True, width="stretch")
            st.caption("Positive coefficients increase log-odds in the Logistic Regression comparator. Numeric values were standardized. Coefficients are associative, can be correlated, and do not explain every selected-model prediction.")
            for limitation in report["limitations"]:
                st.write("• " + limitation)
        st.download_button("Download model evaluation", evaluation_export(bundle, source), "model_evaluation.json", "application/json")
    else:
        st.warning("No matching model is loaded. Use the explicit training button when the dataset has adequate dates and class coverage.")
elif page == "Project Guide":
    st.subheader("Supply Chain Performance and Delivery Efficiency Analysis")
    st.write("This project turns validated order records into delivery metrics, evidence-backed investigation priorities and a carefully evaluated estimate of late-delivery risk.")
    with st.expander("How to explain the project in class", expanded=True):
        st.write("I measure delivery at order level using actual customer arrival and the checkout promise. I compare groups and time periods, then evaluate three classifiers on later orders. I exclude outcome information from prediction inputs and report limitations alongside recommendations.")
    with st.expander("Data provenance"):
        st.json(provenance if is_sample else {"source": source, "kind": "User-uploaded; independently unverified"})
    for label, filename in [("Metric and analysis methodology", "METHODOLOGY.md"),
                             ("Data dictionary", "DATA_DICTIONARY.md"),
                             ("Data flow diagrams", "DATA_FLOW.md"),
                             ("Viva preparation", "VIVA_GUIDE.md"),
                             ("Five-minute demo", "DEMO_SCRIPT.md")]:
        path = ROOT / "docs" / filename
        if path.exists():
            with st.expander(label):
                st.markdown(path.read_text(encoding="utf-8"))
    st.caption("Mermaid source is in docs/DATA_FLOW.md and renders on GitHub; the README includes a static diagram.")

if page in ["Overview", "Explore Data", "Delivery Performance", "Business Insights"]:
    with st.expander("Download this analysis"):
        cols = st.columns(3)
        cols[0].download_button("Cleaned analytical CSV", analytical_export(filtered, source, filters, minimum), "cleaned_orders.csv", "text/csv")
        cols[1].download_button("Filtered summary CSV", safe_csv(summary_frame(filtered, source, filters, minimum)), "filtered_summary.csv", "text/csv")
        cols[2].download_button("Insight report", markdown_report(filtered, source, filters, minimum), "insight_report.md", "text/markdown")
        st.caption("All downloads follow the active filters and include provenance, definitions and limitations.")
with st.expander("Definitions and interpretation"):
    st.write(DEFINITIONS)
    st.caption(LIMITATIONS)
st.caption("SUPPLY CHAIN / Evidence first. Decisions with context.")
