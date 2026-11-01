"""Rebuild a privacy-reduced real sample from the official downloaded ZIP."""
from pathlib import Path
from hashlib import sha256
import argparse
import json
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"

def prepare(archive, sample_size=12000):
    with zipfile.ZipFile(archive) as z:
        def read(name):
            with z.open(name) as stream:
                return pd.read_csv(stream)
        orders = read("olist_orders_dataset.csv")
        customers = read("olist_customers_dataset.csv")[["customer_id", "customer_state"]]
        items = read("olist_order_items_dataset.csv")
        products = read("olist_products_dataset.csv")[["product_id", "product_category_name"]]
        translation = read("product_category_name_translation.csv")
    products = products.merge(translation, on="product_category_name", how="left", validate="many_to_one")
    lines = items.merge(products[["product_id", "product_category_name_english"]], on="product_id", how="left", validate="many_to_one")
    lines["category"] = lines.product_category_name_english.fillna("Unknown")
    item_totals = lines.groupby("order_id").agg(
        sales=("price", "sum"), quantity=("order_item_id", "count"),
        category=("category", lambda s: s.iloc[0] if s.nunique() == 1 else "Mixed")).reset_index()
    joined = orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
    joined = joined.merge(item_totals, on="order_id", how="left", validate="one_to_one")
    selected = joined.sort_values("order_id").sample(n=min(sample_size, len(joined)), random_state=21).sort_values("order_id")
    sample = selected[["order_id", "order_purchase_timestamp", "order_delivered_customer_date",
                       "order_estimated_delivery_date", "order_status", "customer_state",
                       "category", "sales", "quantity"]].rename(columns={
        "order_purchase_timestamp": "order_date", "order_delivered_customer_date": "delivery_date",
        "order_estimated_delivery_date": "promised_date", "order_status": "status", "customer_state": "region"})
    sample["order_id"] = [f"OLIST-{i:06d}" for i in range(1, len(sample)+1)]
    output = ROOT / "data" / "sample" / "olist_orders_sample.csv"
    sample.to_csv(output, index=False, lineterminator="\n")
    metadata = {
        "name": f"Olist real-order sample ({len(sample):,} orders)", "kind": "Real, privacy-reduced historical sample",
        "publisher": "Olist", "source_url": SOURCE, "access_date": "2026-11-01",
        "license": "CC BY-NC-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "attribution": "Olist. Brazilian E-Commerce Public Dataset by Olist. Kaggle. Adapted into an order-level non-commercial teaching sample.",
        "changes": "Random sample (seed 21); item prices summed once per order; categories translated, multi-category orders labeled Mixed; customer linkage removed; order IDs replaced.",
        "source_orders": len(orders), "source_items": len(items), "sample_orders": len(sample),
        "archive_sha256": sha256(Path(archive).read_bytes()).hexdigest(),
        "sample_sha256": sha256(output.read_bytes()).hexdigest(),
        "coverage_start": sample.order_date.min(), "coverage_end": sample.order_date.max(),
        "grain": "One row per distinct order", "financial_rule": "sales = sum of item price, excluding freight; quantity = number of item records",
        "currency": "Source monetary units; no currency assertion in this project.",
        "limitations": [
            "Historical Brazilian marketplace sample, not current or global performance.",
            "No shipping mode, customer segment, discount, profit, carrier ID, inventory or measured savings.",
            "Estimated delivery timestamps are treated as calendar-day promises.",
            "Checkout availability of item attributes and promise is assumed; no event audit log is supplied.",
        ],
    }
    (ROOT / "data" / "sample" / "provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=ROOT / "data/raw/olist.zip")
    parser.add_argument("--sample-size", type=int, default=12000)
    args = parser.parse_args()
    prepare(args.archive, args.sample_size)