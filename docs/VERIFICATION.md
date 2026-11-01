# Version 2 verification — examination edition

Verified on **1 November 2026**, using the existing CPython 3.14.7 pinned environment. No dependency upgrade was needed.

| Check | Actual outcome |
|---|---|
| Full current test suite | **73 passed**, no warnings, 23.62 seconds |
| Legacy delivery/model correctness | All original 45 checks retained and passing |
| Flexible CSV parsing | Comma/semicolon/tab/pipe, quoted multiline text, UTF-16 BOM, Windows encoding, literal NA, headerless and single-column input passed |
| Resource boundaries | Row/column caps and upload limit checks passed; the UI displays 200 MB |
| Larger real parsing workload | **26.91 MB**, **55,000 rows** imported in **0.314 seconds** and profiled in **0.252 seconds** on this machine |
| Long text fields | A 150,000-character field loaded without the old CSV-parser field-size restriction |
| General profiling | Leading-zero identifiers preserved; ambiguous dates/mixed numbers retained as text; explicit decimal-comma conversion passed |
| Privacy and duplicates | Contact patterns beyond the initial preview excluded; duplicate removal uses original source rows and preserves distinct hidden identities |
| Generic app workflow | Import, all six supported chart types, export bundle and delivery-feature guidance passed through Streamlit AppTest |
| Delivery upload workflow | Explicit column mapping, eligibility metrics, optional confirmed ID/status creation and numeric-format normalization passed |
| Malformed input UX | Error displayed with corrective guidance and no application exception |
| Examination controls | Filter reset, lazy exports, guided-demo navigation and manual prediction passed |
| Export correctness | Selected-row ZIP context, formula-safe headers, preserved negative numeric values and escaped printable HTML passed |
| Local launcher | Occupied ports remain untouched; available-port selection and exhausted-port handling passed |
| Reference model compatibility | The existing real-sample artifact still matches the validated dataset fingerprint; no test-based model reselection occurred |
| Native browser test limit | Chrome extension blocked file selection; Windows automation then stopped because it could not verify the active browser URL |

The original NumPy/pandas timedelta warnings were resolved with equivalent explicitly typed day offsets. The reference target, temporal cutoffs, feature list and measured classification experiment are unchanged.

The measured large-file test proves handling above the former 25 MB limit. It does not establish performance for every 200 MB table or every hardware configuration.

## Browser verification scope

The redesigned dashboard and 200 MB file-uploader control were inspected in the browser. Automated CSV import, mapping, charts, exports, training and prediction handlers were exercised using Streamlit's official AppTest runner, with real uploaded-byte fixtures substituted for the file-picker transport.

The final native file-picker interaction was **not completed**. Browser/Windows permissions were not changed. No claim is made that this blocked UI transport check passed.

A separate preview used port 8502 because the user's existing app occupied 8501; that existing process was left alone.

## Reproduce the current checks

    .venv\Scripts\python.exe -m pip check
    .venv\Scripts\python.exe -m pytest -q

For the presentation, double-click **Start Project.cmd** or run:

    .venv\Scripts\python.exe scripts\launch.py

The standard **streamlit run app.py** remains supported. See CSV_WORKSPACE.md for format support, resource limits, privacy/type handling and the distinction between generic rows and eligible delivered orders.

---
# Version 1 verification record (historical)

Verified on **1 November 2026**, using CPython 3.14.7 on Windows and the pinned project environment. Exact package versions are in requirements-lock.txt.

## Executed checks

| Check | Actual outcome |
|---|---|
| Dependency consistency | python -m pip check: no broken requirements |
| Full pytest suite after final layout changes | **45 passed**, 11.06 seconds |
| Hand-check fixture | 6 usable orders, 3 eligible, 2/3 on time; signed mean delay 1/3 day; late-only mean 3 days; sales 2100 |
| Data validation | Empty/malformed CSV, encoding, size, missing columns, explicit/invalid dates, negative/nonfinite values and label mismatch cases passed |
| Order grain and financial totals | Duplicate vs distinct items, consistent repeated totals, conflicting outcomes and sibling invalidation passed |
| Filters and empty population | KPI changes, zero denominators and helpful empty state passed |
| Insight/report consistency | Group rates, minimum evidence, summary metrics, report context and numeric-safe CSV export cases passed |
| Temporal model boundaries | No order overlap, train/validation label availability, feature leakage allowlist and test-target independence cases passed |
| Modeling failure handling | Too few records, single-class targets and unresolved supplied labels rejected as expected |
| Inference and artifacts | Unseen categories, invalid/missing inputs, row association, range warnings and stale artifact rejection passed |
| All seven Streamlit pages | AppTest navigation completed without exceptions |
| Explicit training and prediction | AppTest trained all three comparators; manual prediction displayed an estimate |
| Real sample preparation | Official ZIP read; 99,441 source orders / 112,650 item records; real 12,000-order privacy-reduced sample generated |
| Local server readiness | HTTP /_stcore/health returned ok |
| Browser visual review | Desktop, normal window and 390-pixel phone layouts inspected; truncated KPI cards and chart legend overlap corrected |
| Browser manual prediction | Default form returned 47.4% estimated risk, Late, threshold 0.45; uncertainty warning visible |
| Browser summary download | CSV downloaded; 12,000 total, 11,668 eligible, on-time fraction 10,854 / 11,668; required report context verified |

The suite emits **8 deprecation warnings** concerning NumPy/pandas timedelta interoperability in the pinned versions. They are not test failures. Future dependency upgrades should rerun the checks rather than assuming compatibility.

## Verification limit

The browser-driven CSV file chooser refused the automated test because the Chrome extension's file-URL permission was unavailable. The automated upload check was therefore **not completed**. CSV parsing, validation, mapping behavior and upload-page empty state were tested through Python/AppTest. The application does not require that browser extension for an ordinary person to choose a local CSV.

No security or extension permissions were changed. No public Streamlit app deployment was requested or performed. The public GitHub repository contains source and an appropriately attributed sample, while the app remains local.

## Reproduce

From the project root:

    .venv\Scripts\python.exe -m pip check
    .venv\Scripts\python.exe -m pytest -q
    .venv\Scripts\python.exe scripts\train.py
    .venv\Scripts\python.exe scripts\document_results.py
    .venv\Scripts\python.exe -m streamlit run app.py

On a fresh clone there is no committed joblib binary: train explicitly in the application or with scripts/train.py. The tracked JSON and Markdown show the measured reference experiment.

## Measured model limits

The selected Random Forest has 5.09% precision, 71.43% recall, 0.095 F1 and 0.0588 AP on the fixed test period. It produces 1,677 false late alarms and has worse Brier error than the dummy. This is a limited educational model, not an established operational decision system. The weaker final test result is retained rather than changing selection after seeing it.
