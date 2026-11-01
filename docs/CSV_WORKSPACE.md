# CSV workspace — version 2

## Two useful analysis paths

Every valid supported delimited table can open in **General data exploration**, even when it has no order ID, delivery dates or target label. The application does not invent a delivery rate or train an arbitrary classifier from unrelated data.

To activate **Delivery analytics**, map the actual order-placement, customer-arrival/promise dates (or verified order-to-customer duration fields), status and identifier fields. Confirm the row grain and financial grain. Existing eligibility and leakage rules continue to apply.

“Any CSV” means supported text tables within the documented resource limits; malformed/binary data produces an actionable error. It does not mean every table contains enough information for every supply-chain metric.

## Limits

- Upload: **200 MB per file** by default, increased from 25 MB.
- Table: **1,000,000 rows**, **300 columns** by default.
- General chart sample: at most **50,000 rows**, seed 21, explicitly labeled.
- Scatter display: at most **10,000 points** from the chart sample.
- Local model training: at most **100,000 eligible orders**; larger tables retain descriptive analytics.
- Batch prediction: **10,000 rows**, using the selected model's required inputs.

SC_UPLOAD_LIMIT_MB, SC_MAX_ROWS and SC_MAX_COLUMNS configure the parser. The uploader passes the configured MB limit directly to Streamlit, and .streamlit/config.toml also defaults to 200 MB. Available RAM still limits practical processing: start with smaller, focused tables on low-memory computers.

A measured **26.91 MB / 55,000-row** test table imported and profiled successfully. The verification record contains measured times; no claim is made that the largest possible file/shape was benchmarked.

## Import options

CSV, TSV and delimited TXT are accepted. Auto mode recognizes comma, semicolon, tab and pipe separators. You can select the separator explicitly if detection is inconclusive. Quoted fields and multiline quoted text are supported.

Encoding choices: Auto, UTF-8, UTF-16, Windows-1252 and Latin-1. Auto checks a UTF-16 byte-order mark, then UTF-8, then Windows-1252; the chosen encoding is displayed. Check accented characters and select another encoding if needed.

Uncheck First row contains column names for headerless files. Optional header repair supplies blank names and disambiguates duplicates with suffixes. The import summary records repairs. Malformed records are rejected rather than silently skipped.

Only empty cells and whitespace-only cells count as missing by default. The literal text NA remains text, which matters for regional/category codes. Declare optional exact missing-value markers such as NULL,N/A explicitly when your source uses them; changing import options invalidates prepared exports.

## General explorer

- Data preview with visible-column selection and 100 / 250 / 1,000-row display.
- Per-column type, missing count, missing percentage and distinct-value count.
- Conservative numeric inference: every populated value must parse to a finite number. Leading-zero codes and identifiers retain text semantics.
- ISO date inference only; ambiguous day/month strings remain text.
- Explicit decimal-mark selection; thousands separators and currencies are not guessed.
- Literal text search, up to two categorical filters and two numeric-range filters.
- Category counts, distributions, group comparison, scatter plots, numeric correlations and time trends when the needed columns exist.
- Source-row counts are labeled as rows, never orders.

Duplicate removal is off by default. If you turn it on, only exact duplicates of the original source rows are removed. Repeated visible rows can still represent distinct source records whose private fields were excluded.

Detected contact, fine-location and credential fields are excluded from previews/charts/exports. Email and international-phone patterns are checked across the loaded columns. Automatic detection cannot establish every field's meaning: review the visible columns before sharing an export.

## Delivery mapping improvements

Aliases recognize capitalization, spaces, underscores and punctuation. Multiple candidate columns stay ambiguous until explicitly mapped. No shipping/carrier-handover date is silently used as customer arrival.

If order IDs are absent, an explicit checkbox can treat each source row as one order and create local row IDs. This is only allowed for order-grain input. If status is absent, a separate explicit confirmation can derive delivered from a recorded customer-arrival date; other rows remain unknown. Invalid arrival dates are still rejected by validation.

The delivery mapper includes explicit decimal-mark and thousands-separator choices for numeric business fields. Identifiers and dates are not altered by these choices. Currency symbols and units are not guessed.

Optional fields remain optional. A generic table stays usable while you decide whether a valid delivery interpretation exists.

## Downloads and presentation

General exports contain selected_data.csv, column_profile.csv, report_context.json and README.md in a ZIP. Profiles describe the full prepared table; selected_data.csv follows filters. The manifest states the source, generation time, filters, analytical unit, actions and limitations.

Delivery downloads are prepared only when requested, then retained in the current session. They include cleaned CSV, filtered summary, Markdown insights and a self-contained printable HTML report. Report metadata appears on the first analytical CSV data row instead of being repeated a million times. The model-evaluation download continues to describe the full fixed holdout.

Text values and CSV headers are protected against spreadsheet-formula injection; legitimate negative numeric values remain numeric.

Start guided demo restores the real sample, clears delivery filters and walks through the seven pages. Presentation mode keeps source controls compact. Reset all filters and Find order ID support a quick demonstration. Start Project.cmd starts the app on an available local port and opens the browser; it leaves occupied ports alone.
