"""Generate readable measured results directly from stored evaluation and summary."""
from pathlib import Path
import json
import csv
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/"artifacts/model_evaluation.json").read_text())
with (ROOT/"artifacts/sample_summary.csv").open(encoding="utf-8-sig",newline="") as f:
    metrics=next(csv.DictReader(f))
lines=["# Measured results","",
       "These are actual results from the included real Olist 12,000-order sample, not a claimed production benchmark.",
       "",
       "Source: [Olist / Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Accessed 2026-11-01. Data/results: CC BY-NC-SA 4.0.",
       "", "## Descriptive population", ""]
for key in ["total_orders","eligible_orders","excluded_orders","late_orders","on_time_orders","on_time_rate","mean_signed_delay","mean_late_delay","median_delivery_days"]:
    value=metrics[key]
    if key.endswith("_rate"):
        value=f"{float(value):.2%}"
    elif "delay" in key or "days" in key:
        value=f"{float(value):.2f} calendar days"
    lines.append(f"- **{key.replace('_',' ').title()}:** {value}")
lines += ["","See artifacts/data_quality.json for missing values and exclusion reasons. Descriptive figures use all usable sample orders; predictive split counts below differ because unresolved outcomes are excluded and cutoff purges remove late-known outcomes.",
          "","## Chronological periods","",
          "| Split | First order | Last order | Retained orders | Late orders | Late rate |",
          "|---|---|---|---:|---:|---:|"]
for name,split in report["split"]["splits"].items():
    lines.append(f"| {name.title()} | {split['start']} | {split['end']} | {split['orders']:,} | {split['late_orders']:,} | {split['late_rate']:.2%} |")
lines += ["",f"Purged for label availability: {report['split']['purged_train_orders']} training orders and {report['split']['purged_validation_orders']} validation orders. Label availability is delivery day + one day; actual administrative delays are unknown.",
          "","## Final untouched test results","",
          "| Model | Accuracy | Late precision | Late recall | Late F1 | ROC-AUC | PR-AUC/AP | Brier error | Threshold |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
for name,s in report["test"].items():
    lines.append(f"| {name} | {s['accuracy']:.3f} | {s['precision']:.3f} | {s['recall']:.3f} | {s['f1']:.3f} | {s['roc_auc']:.3f} | {s['pr_auc_ap']:.3f} | {s['brier_score']:.3f} | {report['thresholds'][name]:.2f} |")
selected=report["selected_model"]
score=report["test"][selected]
matrix=score["confusion_matrix"]
lines += ["",f"**Selected by validation: {selected}, threshold {report['threshold']:.2f}.**",
          "",f"The test set contains {matrix[1][0]+matrix[1][1]:,} late orders. The selected model catches {matrix[1][1]:,}, misses {matrix[1][0]:,}, and raises {matrix[0][1]:,} false late alarms. This is weak precision and should be presented as a limited educational experiment.",
          "",
          "The majority-class dummy achieves high accuracy while catching no late orders. The selected model improves ranking over a constant probability but has substantially worse Brier error. Its balanced class weights and validation-selected threshold do not produce reliable operational probabilities on this later period.",
          "",
          "Logistic Regression has better AP than the selected Random Forest on this particular test period. The model was not switched after seeing test results: selection used validation AP only. Validation late prevalence differs substantially from train/test, demonstrating temporal drift and the limitations of one historical split.",
          "",
          "## Calibration and interpretation",
          "",
          "The application shows six test quantile reliability bins and Brier score. No post-hoc calibration was fitted. Risk estimates are not guaranteed confidence. Coefficients belong to the Logistic Regression comparator and do not establish causal effects.",
          "",
          "## Features and protocol",
          "", "- Prediction moment: order placement, conditional on eventual observed delivery.",
          "- Included: " + ", ".join(report["features"]) + ".",
          "- Preprocessing: train-only numeric imputation/scaling and categorical imputation/one-hot encoding.",
          "- Selection: " + report["selection"],
          "",
          "## Limitations",
          ""]
lines += ["- " + item for item in report["limitations"]]
lines += ["", "No shipping-mode, profit, discount, inventory, carrier or savings result is inferred from absent fields. See METHODOLOGY.md and VERIFICATION.md for the protocol and executed checks."]
(ROOT/"docs/RESULTS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("Wrote docs/RESULTS.md from measured artifacts.")
