"""Supply Chain Performance and Delivery Efficiency Analysis — local college project."""
from pathlib import Path
import json
import hashlib
from src.ui import inject_theme, header, context_strip, clear_filters, start_demo, demo_controls, PAGES
from src.import_ui import upload_workspace
from src.general_ui import render_general
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
from src.reporting import analytical_export, summary_frame, safe_csv, markdown_report, evaluation_export, html_report, LIMITATIONS
from src.visualizations import style, outcome_chart, group_chart, trend_chart, distribution, correlation_chart

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Supply Chain | Delivery Intelligence", page_icon="📦", layout="wide")
inject_theme()

@st.cache_data
def sample_data():
    return prepare_orders(pd.read_csv(ROOT / "data/sample/olist_orders_sample.csv", dtype=str))

def number(value, suffix="", percentage=False):
    if value is None or pd.isna(value):
        return "Not available"
    return f"{value:.1%}" if percentage else f"{value:,.1f}{suffix}"

with st.sidebar:
    st.markdown('<div class="brand"><div class="brandmark">◈</div><div><strong>SupplyLens</strong><small>DELIVERY INTELLIGENCE</small></div></div>', unsafe_allow_html=True)
    page=st.radio("Workspace",PAGES,key="page")
    st.divider()
    st.button("Start guided demo",on_click=start_demo,width="stretch",type="primary")
    presentation=st.toggle("Presentation mode",key="presentation_mode",
                           help="Keeps source details compact while you present. Analysis and model results do not change.")
    with st.expander("Data & analysis settings",expanded=not presentation):
        data_choice=st.radio("Dataset",["Load sample data","Upload CSV"],key="data_choice")
        minimum=st.number_input("Minimum group size",min_value=5,max_value=500,value=30,step=5,
                                help="Smaller groups remain visible but do not enter ranked insights.")
    st.caption("v2.0 · Built for clear, evidence-backed explanations")

provenance = json.loads((ROOT / "data/sample/provenance.json").read_text(encoding="utf-8"))
if data_choice == "Load sample data":
    prepared = sample_data()
    source = provenance["source_url"] + " | Real Olist 12,000-order sample"
    dataset_name = "Olist · 12,000 real orders"
    is_sample = True
else:
    try:
        selection=upload_workspace()
    except ValueError as error:
        st.error(str(error))
        st.info("Adjust the import settings or switch to General data exploration. Your source file is preserved.")
        st.stop()
    if selection.prepared is None:
        render_general(selection,page)
        st.markdown('<div class="footer-note">SUPPLYLENS / Inspect the data. Explain the evidence.</div>',unsafe_allow_html=True)
        st.stop()
    prepared=selection.prepared
    source=selection.source
    dataset_name="Uploaded CSV · delivery analysis"
    is_sample=False

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
    st.button("Reset all filters",on_click=clear_filters,args=(fingerprint,),width="stretch")
    with st.expander("Filter orders", expanded=False):
        filters = {}
        filters["order_search"]=st.text_input("Find order ID",key="order_search_"+fingerprint[:8],help="Literal search applied to metrics, charts and exports.")
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
titles={
    "Overview":("Delivery performance, in focus.","A clear view of delivery reliability, order volume and the areas worth investigating."),
    "Explore Data":("Trust the data before the chart.","Inspect validation results and understand exactly which orders enter the analysis."),
    "Delivery Performance":("See where delays concentrate.","Compare rate, volume and delay severity with a consistent eligible population."),
    "Business Insights":("Turn patterns into better questions.","Computed findings with evidence, a comparison and a practical next investigation."),
    "Predict Delivery Risk":("Assess a new order.","Estimate late-arrival risk using information available at order placement."),
    "Model Evaluation":("Evidence behind the estimate.","Compare three classifiers on later orders, with the limitations in plain sight."),
    "Project Guide":("Ready for your viva.","The data flow, definitions and decisions you can confidently explain."),
}
header(*titles[page])
context_strip([dataset_name,f"{len(filtered):,} selected orders","Unit: distinct order",
               f"Eligible: {metrics['eligible_orders']:,}"])
st.caption("Active filters — "+(" | ".join(active) if active else "All orders"))
if is_sample and not presentation:
    st.caption("Real Olist sample · 2016–2018 · CC BY-NC-SA 4.0 · historical observational data")
demo_controls(page)
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
    with st.expander("Validation detail and exclusion totals",expanded=False):
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
                        values[feature] = col.number_input(label, min_value=minimum_value, max_value=maximum_value, value=max(minimum_value, float(round(default)) if feature in {"quantity","order_month","order_weekday"} else default),
                                                          step=1.0 if feature != "discount" else .01,
                                                          help=f"Training range: {lower:g} to {upper:g}. Weekday: Monday=0.")
                    else:
                        options=report["training_categories"][feature]
                        typical=str(orders[feature].mode().iloc[0]) if not orders[feature].mode().empty else options[0]
                        values[feature] = col.selectbox(label, options, index=options.index(typical) if typical in options else 0)
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
    for label, filename in [("CSV formats and general workspace", "CSV_WORKSPACE.md"),
                             ("Metric and analysis methodology", "METHODOLOGY.md"),
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
    with st.expander("Export centre · take the evidence with you"):
        st.write("Prepare the selected data, a concise summary and a printable report.")
        export_key=hashlib.sha256((fingerprint+source+json.dumps(filters,sort_keys=True,default=str)+str(minimum)).encode()).hexdigest()
        if st.button("Prepare downloads",type="primary",disabled=filtered.empty):
            with st.spinner("Preparing downloads for the active filters…"):
                st.session_state["_delivery_exports"]=(export_key,{
                    "data":analytical_export(filtered,source,filters,minimum),
                    "summary":safe_csv(summary_frame(filtered,source,filters,minimum)),
                    "markdown":markdown_report(filtered,source,filters,minimum),
                    "html":html_report(filtered,source,filters,minimum),
                })
        ready=st.session_state.get("_delivery_exports")
        if ready and ready[0]==export_key:
            files=ready[1]
            cols=st.columns(4)
            cols[0].download_button("Cleaned analytical CSV",files["data"],"cleaned_orders.csv","text/csv")
            cols[1].download_button("Filtered summary CSV",files["summary"],"filtered_summary.csv","text/csv")
            cols[2].download_button("Insight report",files["markdown"],"insight_report.md","text/markdown")
            cols[3].download_button("Printable report",files["html"],"delivery_report.html","text/html")
        st.caption("All downloads follow the active filters. CSV report context is stored on its first data row to keep large exports manageable. Open the HTML report to print or save as PDF.")
with st.expander("Definitions and interpretation"):
    st.write(DEFINITIONS)
    st.caption(LIMITATIONS)
st.markdown('<div class="footer-note">SUPPLYLENS / Evidence first. Decisions with context.</div>',unsafe_allow_html=True)
