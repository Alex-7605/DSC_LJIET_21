"""Validate without overwriting source data or silently resolving order conflicts."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

DATES = ["order_date", "delivery_date", "promised_date"]
NUMBERS = ["sales", "profit", "discount", "quantity", "actual_days", "scheduled_days", "supplied_late"]
DIMENSIONS = ["region", "category", "shipping_mode", "segment"]
DELIVERED = {"delivered", "complete", "completed"}
CANCELLED = {"cancelled", "canceled", "shipping canceled"}
KNOWN_STATUS = DELIVERED | CANCELLED | {"shipped", "processing", "unavailable", "invoiced", "created", "approved", "unknown"}

@dataclass
class PreparedData:
    orders: pd.DataFrame
    quality: dict
    exclusions: pd.DataFrame

def parse_dates(series, date_format):
    s = series.astype("string").str.strip()
    if date_format == "ISO8601":
        mask = s.str.match(r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$", na=False)
        parsed = pd.to_datetime(s.where(mask), format="ISO8601", errors="coerce")
    else:
        parsed = pd.to_datetime(s, format=date_format, errors="coerce")
    return parsed, s.notna() & parsed.isna()

def prepare_orders(raw, date_format="ISO8601", grain="order", financial_grain="item"):
    if "order_id" not in raw or "order_date" not in raw or "status" not in raw:
        raise ValueError("Map order_id, order_date and status before analysis.")
    dates_supported = {"delivery_date", "promised_date"}.issubset(raw.columns)
    durations_supported = {"actual_days", "scheduled_days"}.issubset(raw.columns)
    if not dates_supported and not durations_supported:
        raise ValueError("Map delivery_date + promised_date, or verified order-to-delivery actual_days + scheduled_days.")
    if grain not in {"order", "item"} or financial_grain not in {"order", "item"}:
        raise ValueError("Choose valid analytical and financial grain settings.")
    if grain == "item" and "item_id" not in raw:
        raise ValueError("Item-level input requires item_id to distinguish legitimate identical items from duplicates.")
    data = raw.copy(deep=True)
    quality = {"rows_loaded": len(data), "missing_values": data.isna().sum().to_dict()}
    duplicates = int(data.duplicated().sum())
    data = data.drop_duplicates().reset_index(drop=True)
    quality["exact_duplicates_removed"] = duplicates
    reasons = pd.Series("", index=data.index, dtype="string")
    def flag(mask, reason):
        nonlocal reasons
        reasons.loc[mask.fillna(False)] += reason + "; "
    data["order_id"] = data.order_id.astype("string").str.strip()
    flag(data.order_id.isna() | data.order_id.eq(""), "missing order identifier")
    for col in DATES:
        if col not in data:
            data[col] = pd.NaT
        else:
            data[col], invalid = parse_dates(data[col], date_format)
            flag(invalid, f"invalid or ambiguous {col}")
    flag(data.order_date.isna(), "missing order date")
    for col in NUMBERS:
        if col in data:
            original = data[col]
            values = pd.to_numeric(original, errors="coerce")
            invalid = original.notna() & (values.isna() | ~np.isfinite(values))
            flag(invalid, f"invalid numeric {col}")
            data[col] = values
    for col in ["actual_days", "scheduled_days", "sales", "quantity"]:
        if col in data:
            flag(data[col].lt(0), f"negative {col}")
    if "quantity" in data:
        flag(data.quantity.notna() & ((data.quantity % 1 != 0) | data.quantity.eq(0)), "quantity must be a positive integer")
    if "discount" in data:
        flag(data.discount.notna() & ~data.discount.between(0, 1), "discount must be a fraction 0 to 1")
    if "supplied_late" in data:
        flag(data.supplied_late.notna() & ~data.supplied_late.isin([0, 1]), "supplied label must be 0 or 1")
    data["status"] = data.status.astype("string").str.strip().str.lower().fillna("unknown")
    quality["unrecognized_status_rows"] = int((~data.status.isin(KNOWN_STATUS)).sum())
    for col in DIMENSIONS:
        if col in data:
            data[col] = data[col].astype("string").str.strip().fillna("Unknown").replace("", "Unknown")
            flag(data[col].str.len().gt(120), f"{col} exceeds 120 characters")
    flag(data.delivery_date.notna() & data.delivery_date.lt(data.order_date), "delivery before order")
    flag(data.promised_date.notna() & data.promised_date.dt.normalize().lt(data.order_date.dt.normalize()), "promise before order")
    # Invalid lines invalidate the whole order; partial removal could understate value.
    bad_ids = data.loc[reasons.ne(""), "order_id"].dropna()
    flag(data.order_id.isin(bad_ids) & reasons.eq(""), "another row in order is invalid")
    excluded_rows = data.loc[reasons.ne(""), ["order_id"]].assign(reason=reasons[reasons.ne("")].values)
    data = data.loc[reasons.eq("")].copy()
    repeated_rows = int(data.order_id.duplicated().sum())
    conflicts = []
    if grain == "item":
        bad_keys = data.duplicated(["order_id", "item_id"], keep=False) | data.item_id.isna()
        conflicts.extend(data.loc[bad_keys, "order_id"].tolist())
    check_columns = ["order_date", "delivery_date", "promised_date", "status", "actual_days", "scheduled_days", "region", "shipping_mode", "segment", "supplied_late"]
    if grain == "order":
        conflicts = data.loc[data.order_id.duplicated(keep=False), "order_id"].unique().tolist()
    else:
        for col in check_columns:
            if col in data:
                counts = data.groupby("order_id")[col].nunique(dropna=False)
                conflicts.extend(counts[counts.gt(1)].index.tolist())
        if financial_grain == "order":
            for col in ["sales", "profit", "discount", "quantity"]:
                if col in data:
                    counts = data.groupby("order_id")[col].nunique(dropna=False)
                    conflicts.extend(counts[counts.gt(1)].index.tolist())
    conflicts = set(conflicts)
    conflict_exclusions = pd.DataFrame({"order_id": sorted(conflicts), "reason": "conflicting order records / wrong grain"})
    data = data.loc[~data.order_id.isin(conflicts)]
    aggregations = {}
    for col in data.columns:
        if col == "order_id":
            continue
        if col in ["sales", "profit", "quantity"] and grain == "item" and financial_grain == "item":
            aggregations[col] = lambda values: values.sum(min_count=1) if values.notna().all() else np.nan
        elif col == "category" or (col == "discount" and grain == "item"):
            aggregations[col] = lambda values: values.iloc[0] if values.nunique(dropna=False) == 1 else ("Mixed" if values.dtype.kind not in "fi" else np.nan)
        else:
            aggregations[col] = "first"
    orders = data.sort_values("order_id").reset_index(drop=True) if grain == "order" else data.groupby("order_id", as_index=False).agg(aggregations)
    if dates_supported:
        # Calendar-day promise: arrival on the estimated date is on time.
        orders["actual_days"] = (orders.delivery_date.dt.normalize() - orders.order_date.dt.normalize()).dt.days.astype(float)
        orders["scheduled_days"] = (orders.promised_date.dt.normalize() - orders.order_date.dt.normalize()).dt.days.astype(float)
    orders["delay_days"] = orders.actual_days - orders.scheduled_days
    valid_outcome = orders.actual_days.notna() & orders.scheduled_days.notna()
    orders["eligible"] = orders.status.isin(DELIVERED) & valid_outcome
    orders["exclusion_reason"] = np.select(
        [orders.status.isin(CANCELLED), ~orders.status.isin(DELIVERED), ~valid_outcome],
        ["cancelled", "undelivered / unknown status", "missing delivery outcome"], default="")
    orders["late"] = orders.delay_days.gt(0).astype("Int64").where(orders.eligible)
    orders["delivery_outcome"] = np.select(
        [~orders.eligible, orders.late.fillna(0).eq(1)], ["Excluded / unknown", "Late"], default="On time")
    orders["order_month"] = orders.order_date.dt.month
    orders["order_weekday"] = orders.order_date.dt.dayofweek
    mismatch = pd.Series(False, index=orders.index)
    if "supplied_late" in orders:
        mismatch = orders.eligible & orders.supplied_late.notna() & orders.supplied_late.ne(orders.late)
    orders["label_mismatch"] = mismatch.fillna(False)
    quality.update({
        "repeated_order_rows": repeated_rows,
        "conflicting_orders": len(conflicts),
        "invalid_record_rows": len(excluded_rows),
        "usable_orders": len(orders),
        "eligible_orders": int(orders.eligible.sum()),
        "unknown_or_excluded_orders": int((~orders.eligible).sum()),
        "label_mismatches": int(mismatch.sum()),
        "actions": ["Original data retained separately in memory.", "Only mapped, allowlisted columns retained.",
                    "Exact duplicates removed.", "Invalid lines and all sibling order lines excluded.",
                    f"Input grain: {grain}; financial grain: {financial_grain}.",
                    "Calendar-day order-to-customer-delivery durations used when dates exist.",
                    "Repeated items aggregated; conflicting order outcomes excluded.",
                    "Source-label disagreements flagged; model training blocked until resolved."],
    })
    exclusion_parts = [excluded_rows, conflict_exclusions, orders.loc[~orders.eligible, ["order_id", "exclusion_reason"]].rename(columns={"exclusion_reason": "reason"})]
    nonempty_parts = [part.astype({"order_id": "string", "reason": "string"}) for part in exclusion_parts if not part.empty]
    exclusions = pd.concat(nonempty_parts, ignore_index=True) if nonempty_parts else pd.DataFrame(columns=["order_id", "reason"])
    quality["exclusion_counts"] = exclusions.reason.value_counts().to_dict()
    return PreparedData(orders.reset_index(drop=True), quality, exclusions)