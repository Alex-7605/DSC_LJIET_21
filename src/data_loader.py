"""Bounded CSV ingestion with explicit dialect/encoding choices and safe mappings."""
from io import StringIO
import csv
import os
import re
import pandas as pd

MAX_UPLOAD_MB = int(os.environ.get("SC_UPLOAD_LIMIT_MB", "200"))
MAX_ROWS = int(os.environ.get("SC_MAX_ROWS", "1000000"))
MAX_COLUMNS = int(os.environ.get("SC_MAX_COLUMNS", "300"))
ALIASES = {
    "item_id": ["order_item_id", "Order Item ID", "line_id"],
    "order_id": ["Order ID", "Order Id", "order_number", "order_no"],
    "order_date": ["order_purchase_timestamp", "Order Date", "order_placed_at", "purchase_date"],
    "delivery_date": ["order_delivered_customer_date", "Delivery Date", "actual_delivery_date", "delivered_at", "arrival_date"],
    "promised_date": ["order_estimated_delivery_date", "Promised Date", "estimated_delivery_date", "expected_delivery_date", "due_date"],
    "status": ["order_status", "Order Status"],
    "region": ["customer_state", "Region", "Order Region", "destination_region", "state"],
    "category": ["product_category_name_english", "Category Name", "product_category"],
    "sales": ["order_value", "Sales", "order_total", "total_sales"],
    "quantity": ["item_count", "Quantity", "qty"],
    "shipping_mode": ["Shipping Mode", "shipping_method"],
    "segment": ["Customer Segment", "customer_segment"],
    "discount": ["Discount", "discount_rate"],
    "profit": ["Profit"],
    "actual_days": ["Actual Delivery Days", "actual_delivery_days"],
    "scheduled_days": ["Scheduled Delivery Days", "scheduled_delivery_days"],
    "supplied_late": ["Late_delivery_risk", "is_late"],
}
FIELDS = list(ALIASES)

def normalized_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())

def decode_csv(payload, encoding):
    if encoding == "auto":
        candidates = ["utf-16"] if payload.startswith((b"\xff\xfe", b"\xfe\xff")) else ["utf-8-sig", "cp1252"]
        for candidate in candidates:
            try:
                return payload.decode(candidate, errors="strict"), candidate
            except UnicodeError:
                continue
        raise ValueError("Encoding could not be detected. Choose the original file encoding explicitly.")
    try:
        return payload.decode(encoding, errors="strict"), encoding
    except (UnicodeError, LookupError) as exc:
        raise ValueError("Encoding could not be read. Select UTF-8, UTF-16, Windows-1252 or Latin-1.") from exc

def read_csv_bytes(payload: bytes, encoding="utf-8-sig", filename="upload.csv", delimiter="auto",
                   has_header=True, normalize_headers=False):
    if not filename.lower().endswith((".csv", ".tsv", ".txt")):
        raise ValueError("Only CSV, TSV and delimited text files are supported.")
    if not payload or not payload.strip():
        raise ValueError("The file is empty.")
    if len(payload) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"File exceeds the configured {MAX_UPLOAD_MB} MB limit.")
    text, actual_encoding = decode_csv(payload, encoding)
    if "\x00" in text:
        raise ValueError("Binary or NUL-containing files are not CSV.")
    if delimiter == "auto":
        try:
            delimiter = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = "\t" if filename.lower().endswith(".tsv") else ","
    if delimiter not in {",", ";", "\t", "|"}:
        raise ValueError("Choose comma, semicolon, tab or pipe as the separator.")
    csv.field_size_limit(MAX_UPLOAD_MB * 1024 * 1024)
    actions = []
    try:
        reader = csv.reader(StringIO(text), delimiter=delimiter, strict=True)
        first = next(reader)
        if not first or len(first) > MAX_COLUMNS:
            raise ValueError(f"CSV must have between 1 and {MAX_COLUMNS} columns.")
        header = first if has_header else [f"column_{i+1}" for i in range(len(first))]
        header = [name.strip() for name in header]
        if not all(header) or len(set(header)) != len(header):
            if not normalize_headers:
                raise ValueError("CSV needs a unique, nonblank header. Enable header repair to rename duplicate or empty columns.")
            seen, repaired = set(), []
            for i, name in enumerate(header):
                base = name or f"column_{i+1}"
                current, number = base, 2
                while current in seen:
                    current = f"{base}_{number}"
                    number += 1
                seen.add(current)
                repaired.append(current)
            header = repaired
            actions.append("Blank/duplicate column headers renamed; source bytes were preserved.")
        count = 0 if has_header else 1
        for row_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != len(first):
                raise ValueError(f"Malformed CSV: record {row_number} has {len(row)} fields; expected {len(first)}. Check the separator and quotes.")
            count += 1
            if count > MAX_ROWS:
                raise ValueError(f"Maximum {MAX_ROWS:,} rows per upload. Split this file into smaller CSVs.")
        if count == 0:
            raise ValueError("CSV contains a header but no records.")
        frame = pd.read_csv(StringIO(text), sep=delimiter, header=0 if has_header else None,
                            names=header, dtype=str, keep_default_na=False, na_values=[""],
                            on_bad_lines="error")
    except (csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError, StopIteration) as exc:
        raise ValueError("Malformed or empty CSV. Check the separator, encoding and quotation marks.") from exc
    frame.attrs["csv_import"] = {"encoding": actual_encoding, "delimiter": repr(delimiter),
                                 "rows": len(frame), "columns": len(frame.columns), "actions": actions}
    return frame

def suggest_mapping(columns):
    mapping, ambiguous = {}, []
    for field, aliases in ALIASES.items():
        known = {normalized_name(name) for name in [field, *aliases]}
        hits = [c for c in columns if normalized_name(c) in known]
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
    return raw[chosen].rename(columns={v: k for k, v in mapping.items() if v}).copy()

def normalize_numeric_columns(frame, decimal=".", thousands=None):
    """Apply an explicitly chosen numeric convention, never to identifiers/dates."""
    if decimal not in {".", ","} or thousands not in {None, ",", ".", " "}:
        raise ValueError("Choose a supported decimal mark and thousands separator.")
    if decimal == thousands:
        raise ValueError("Decimal mark and thousands separator must be different.")
    result=frame.copy()
    for col in ["sales","profit","discount","quantity","actual_days","scheduled_days","supplied_late"]:
        if col not in result:
            continue
        values=result[col].astype("string").str.strip()
        if thousands==" ":
            values=values.str.replace(r"[ \u00a0\u202f]","",regex=True)
        elif thousands:
            values=values.str.replace(thousands,"",regex=False)
        if decimal==",":
            values=values.str.replace(",",".",regex=False)
        result[col]=values
    return result
