# Verification record

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
