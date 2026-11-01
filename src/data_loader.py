"""Bounded, explicit CSV reading. Uploaded data stays in session memory."""
from io import StringIO
import csv
import os
import pandas as pd

MAX_UPLOAD_MB = int(os.environ.get("SC_UPLOAD_LIMIT_MB", "25"))
ALIASES = {"item_id": ["order_item_id", "Order Item ID"],
    "order_id": ["Order ID", "Order Id"],
    "order_date": ["order_purchase_timestamp", "Order Date"],
    "delivery_date": ["order_delivered_customer_date", "Delivery Date"],
    "promised_date": ["order_estimated_delivery_date", "Promised Date"],
    "status": ["order_status", "Order Status"],
    "region": ["customer_state", "Region", "Order Region"],
    "category": ["product_category_name_english", "Category Name"],
    "sales": ["order_value", "Sales"],
    "quantity": ["item_count", "Quantity"],
    "shipping_mode": ["Shipping Mode"],
    "segment": ["Customer Segment"],
    "discount": ["Discount"],
    "profit": ["Profit"],
    "actual_days": ["Actual Delivery Days"],
    "scheduled_days": ["Scheduled Delivery Days"],
    "supplied_late": ["Late_delivery_risk"],
}
FIELDS = list(ALIASES)

def read_csv_bytes(payload: bytes, encoding="utf-8-sig", filename="upload.csv"):
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported.")
    if not payload or not payload.strip():
        raise ValueError("The file is empty.")
    if len(payload) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"File exceeds the configured {MAX_UPLOAD_MB} MB limit.")
    try:
        text = payload.decode(encoding, errors="strict")
    except (UnicodeError, LookupError) as exc:
        raise ValueError("Encoding could not be read. Select UTF-8, Windows-1252 or Latin-1 explicitly.") from exc
    if "\x00" in text:
        raise ValueError("Binary or NUL-containing files are not CSV.")
    try:
        rows = csv.reader(StringIO(text), strict=True)
        header = next(rows)
        if len(header) < 2 or len(set(header)) != len(header):
            raise ValueError("CSV needs a unique header and at least two columns.")
        for index, row in enumerate(rows, start=2):
            if row and len(row) != len(header):
                raise ValueError(f"Malformed CSV: row {index} has a different number of fields.")
        frame = pd.read_csv(StringIO(text), dtype=str, keep_default_na=True)
    except (csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError, StopIteration) as exc:
        raise ValueError("Malformed or empty CSV. Check delimiters and quotation marks.") from exc
    if frame.empty:
        raise ValueError("CSV contains a header but no records.")
    if len(frame) > 250_000:
        raise ValueError("Maximum 250,000 rows per upload.")
    return frame

def suggest_mapping(columns):
    """Return only unambiguous matches; user confirms all upload mappings."""
    mapping, ambiguous = {}, []
    for field, aliases in ALIASES.items():
        hits = [c for c in columns if c == field or c in aliases]
        if len(hits) == 1:
            mapping[field] = hits[0]
        elif len(hits) > 1:
            ambiguous.append(field)
    return mapping, ambiguous

def apply_mapping(raw, mapping):
    chosen = [v for v in mapping.values() if v]
    if len(chosen) != len(set(chosen)):
        raise ValueError("One source column cannot map to multiple analytical fields.")
    if any(v not in raw.columns for v in chosen):
        raise ValueError("Mapping references an unknown source column.")
    # Allowlist prevents customer names, emails and addresses reaching analytics.
    return raw[chosen].rename(columns={v: k for k, v in mapping.items() if v}).copy()