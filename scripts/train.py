"""Explicit training workflow. Never triggered by dashboard filter changes."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from src.validation import prepare_orders
from src.modeling import train_models, save_local_bundle
from src.reporting import markdown_report, summary_frame, safe_csv, context
import json

def main():
    raw = pd.read_csv(ROOT / "data/sample/olist_orders_sample.csv", dtype=str)
    prepared = prepare_orders(raw)
    bundle = train_models(prepared.orders, placement_confirmed=True)

    source = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce | Real 12,000-order sample"
    metadata = context(source, {"scope": "Full sample; fixed chronological holdout"})
    metadata["dataset_limitations"] = metadata.pop("limitations")
    bundle["report"].update(metadata)
    save_local_bundle(bundle, ROOT / "artifacts")
    (ROOT / "artifacts/sample_insights.md").write_bytes(markdown_report(prepared.orders, source, {}))
    (ROOT / "artifacts/sample_summary.csv").write_bytes(safe_csv(summary_frame(prepared.orders, source, {})))
    (ROOT / "artifacts/data_quality.json").write_text(json.dumps(prepared.quality, indent=2, default=int), encoding="utf-8")
    print("Selected:", bundle["report"]["selected_model"])
    print("Threshold:", bundle["report"]["threshold"])
    print(json.dumps(bundle["report"]["test"], indent=2))

if __name__ == "__main__":
    main()