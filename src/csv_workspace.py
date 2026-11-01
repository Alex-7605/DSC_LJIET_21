"""Schema-independent profiling. Source rows are preserved; no delivery facts are inferred."""
from dataclasses import dataclass
from io import BytesIO
from datetime import datetime, timezone
import json
import re
import zipfile
import numpy as np
import pandas as pd
from src.data_loader import normalized_name
from src.reporting import safe_csv

CHART_ROWS = 50000
SENSITIVE_NAMES = {"name", "firstname", "lastname", "fullname", "customername", "suppliername",
                   "email", "emailaddress", "phone", "phonenumber", "mobile", "telephone",
                   "address", "street", "streetaddress", "customeraddress", "postcode",
                   "postalcode", "zipcode", "customerzipcodeprefix", "latitude", "longitude",
                   "customerid", "customeruniqueid", "customer", "client", "patient", "employee", "person", "contact", "ssn", "password", "apikey", "accesstoken"}
IDENTIFIER_PATTERN = re.compile(r"(^|_)(id|code|number|no|zip|postal)(_|$)", re.I)

@dataclass
class GeneralDataset:
    frame: pd.DataFrame
    profile: pd.DataFrame
    hidden_columns: list
    numeric_columns: list
    date_columns: list
    category_columns: list
    actions: list

def sensitive_columns(frame):
    hidden = []
    for col in frame:
        name = normalized_name(col)
        values = frame[col].dropna().astype(str).str.strip()
        named = name in SENSITIVE_NAMES or any(token in name for token in ["email", "password", "accesstoken", "phone", "streetaddress"])
        emails = values.str.contains(r"[^\s@]+@[^\s@]+\.[^\s@]+", regex=True).any()
        phones = values.str.contains(r"^\+\d[\d ()-]{7,}$", regex=True).any()
        if named or emails or phones:
            hidden.append(col)
    return hidden

def infer_general(raw, decimal=".", remove_duplicates=False):
    hidden = sensitive_columns(raw)
    frame = raw.drop(columns=hidden).copy()
    frame = frame.replace(r"^\s*$", np.nan, regex=True)
    actions = ["Source file retained separately; whitespace-only cells treated as missing.",
               f"{len(hidden)} detected contact, identifier or location columns hidden."]
    if remove_duplicates:
        before = len(frame)
        frame = frame.loc[~raw.duplicated()]
        actions.append(f"Removed {before-len(frame):,} exact duplicate rows by explicit choice.")
    numeric, dates, categories, records = [], [], [], []
    for col in frame:
        original = frame[col]
        sample = original.dropna().astype(str).head(10000).str.strip()
        name = re.sub(r"[^a-z0-9]+", "_", str(col).lower())
        identifier = bool(IDENTIFIER_PATTERN.search(name)) or normalized_name(col).endswith("id")
        leading_zero = sample.str.match(r"^0\d+$").any()
        kind = "Text"
        if len(sample) and not identifier and not leading_zero:
            candidates = sample.str.replace(",", ".", regex=False) if decimal == "," else sample
            parsed = pd.to_numeric(candidates, errors="coerce")
            # Do not silently coerce a mostly numeric column with invalid entries.
            if parsed.notna().all() and np.isfinite(parsed).all():
                all_values = original.astype("string").str.strip()
                if decimal == ",":
                    all_values = all_values.str.replace(",", ".", regex=False)
                full = pd.to_numeric(all_values, errors="coerce")
                if int(full.notna().sum()) == int(original.notna().sum()) and np.isfinite(full.dropna()).all():
                    frame[col] = full.astype(float)
                    numeric.append(col)
                    kind = "Numeric"
            if kind == "Text" and sample.str.match(r"^\d{4}-\d{2}-\d{2}(?:[ T].*)?$").all():
                parsed_dates = pd.to_datetime(original, format="ISO8601", errors="coerce")
                if int(parsed_dates.notna().sum()) == int(original.notna().sum()):
                    # Mixed/offset timezones stay text rather than guessing a business timezone.
                    if pd.api.types.is_datetime64_any_dtype(parsed_dates):
                        frame[col] = parsed_dates
                        dates.append(col)
                        kind = "Date / time"
        if kind == "Text" and not identifier:
            categories.append(col)
        records.append({"Column": col, "Type": "Identifier / code" if identifier else kind,
                        "Missing": int(frame[col].isna().sum()),
                        "Missing %": round(float(frame[col].isna().mean()*100), 2) if len(frame) else 0.,
                        "Distinct": int(frame[col].nunique(dropna=True))})
    return GeneralDataset(frame, pd.DataFrame(records), hidden, numeric, dates, categories, actions)

def filter_general(frame, search="", search_columns=None, categories=None, numeric=None):
    result = frame
    if search.strip() and search_columns:
        mask = pd.Series(False, index=result.index)
        for col in search_columns[:5]:
            mask |= result[col].astype("string").str.contains(search.strip(), case=False, regex=False, na=False)
        result = result.loc[mask]
    for col, values in (categories or {}).items():
        if values:
            result = result.loc[result[col].astype(str).isin(values)]
    for col, limits in (numeric or {}).items():
        result = result.loc[result[col].between(*limits)]
    return result.copy()

def sample_for_charts(frame, maximum=CHART_ROWS):
    return frame.sample(maximum, random_state=21) if len(frame) > maximum else frame

def general_bundle(frame, dataset, source, filters):
    """ZIP avoids repeating a long manifest on every row of a large CSV."""
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source, "filters": filters, "analytical_unit": "Source row; not assumed to be an order",
        "exported_rows": len(frame), "exported_columns": list(frame),
        "hidden_columns": dataset.hidden_columns, "cleaning_actions": dataset.actions,
        "definitions": "Row/column counts and missingness describe the selected table; no delivery target is inferred.",
        "limitations": "Source provenance and field semantics are unverified. Automatic type/PII detection is conservative, not a guarantee. Charts label any sampling. Review fields before sharing.",
    }
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("selected_data.csv", safe_csv(frame))
        archive.writestr("column_profile.csv", safe_csv(dataset.profile))
        archive.writestr("report_context.json", json.dumps(metadata, indent=2, default=str))
        archive.writestr("README.md", "# CSV exploration export\n\nOpen selected_data.csv for the selected rows, column_profile.csv for full-table quality, and report_context.json for source, filters, definitions and limitations.\n")
    return buffer.getvalue()
