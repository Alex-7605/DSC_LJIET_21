"""Exports use the same filtered orders and metric functions as the dashboard."""
from datetime import datetime, timezone
import json
import pandas as pd
from src.metrics import kpis, DEFINITIONS
from src.insights import build_insights

LIMITATIONS = (
    "Historical observational data; associations are not causal. Cancelled, undelivered and unknown "
    "outcomes are excluded from delivery-rate denominators. Small groups are unstable. "
    "No measured savings, carrier quality, inventory efficiency or current service guarantees are inferred."
)

def safe_csv(frame):
    result = frame.copy()
    def guard(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
            return "'" + value
        return value
    for col in result.columns:
        if not pd.api.types.is_numeric_dtype(result[col]):
            result[col] = result[col].map(guard)
    return result.to_csv(index=False).encode("utf-8-sig")

def context(source, filters):
    return {
        "dataset_source": source,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "filters": json.dumps(filters, default=str, ensure_ascii=False),
        "analytical_unit": "Distinct order",
        "metric_definitions": DEFINITIONS,
        "eligible_population": "Delivered/completed orders with valid actual and scheduled delivery durations.",
        "limitations": LIMITATIONS,
    }

def summary_frame(orders, source, filters, minimum=30):
    row = {**context(source, filters), **kpis(orders)}
    row["key_findings"] = " | ".join(i["evidence"] for i in build_insights(orders, minimum))
    return pd.DataFrame([row])

def analytical_export(orders, source, filters, minimum=30):
    # Privacy allowlist already enforced before analytics. Include report provenance.
    frame = orders.copy()
    for key, value in context(source, filters).items():
        frame["report_" + key] = value
    frame["report_key_findings"] = " | ".join(i["evidence"] for i in build_insights(orders, minimum))
    return safe_csv(frame)

def markdown_report(orders, source, filters, minimum=30):
    meta = context(source, filters)
    lines = ["# Supply Chain Performance and Delivery Efficiency Analysis", ""]
    lines += [f"- **{key.replace('_', ' ').title()}:** {value}" for key, value in meta.items()]
    lines += ["", "## Metrics", ""]
    lines += [f"- {key}: {value if value is not None else 'Not available'}" for key, value in kpis(orders).items()]
    lines += ["", "## Findings", ""]
    insights = build_insights(orders, minimum)
    if not insights:
        lines.append("Insufficient evidence for a stable above-baseline group finding.")
    for item in insights:
        lines += [f"### {item['finding']}", item["evidence"], item["baseline"], item["uncertainty"],
                  f"Action to consider: {item['action']}", f"Limitation: {item['limitation']}", ""]
    return ("\n\n".join(lines).rstrip() + "\n").encode("utf-8")

def evaluation_export(bundle, source):
    # Filters intentionally do not alter the fixed chronological holdout.
    return json.dumps({**context(source, {"scope": "Full validated dataset; fixed temporal holdout; dashboard filters do not apply"}),
                       "key_findings": bundle["report"]["test"],
                       "evaluation": bundle["report"]}, indent=2, default=str).encode("utf-8")