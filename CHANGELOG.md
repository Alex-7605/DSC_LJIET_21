# Version 2.0 — examination edition

- Redesigned SupplyLens interface with a navy sidebar, compact context chips, consistent cards, clearer charts and responsive layouts.
- Increased uploads from 25 MB to 200 MB; explicit 1,000,000-row and 300-column safeguards.
- General CSV workspace for non-delivery schemas: profiles, search, filters, six chart types and provenance-aware exports.
- CSV/TSV/TXT, common separators, UTF-16/UTF-8/Windows encodings, headerless input and logged header repair.
- Improved explicit delivery mappings, optional row-ID creation and confirmed status derivation.
- Guided viva tour, presentation mode, reset controls, order search and a free-port double-click launcher.
- Lazy report generation and a self-contained printable HTML report.
- CSV formula protection extended to headers; conservative privacy/type handling.
- Faster validation for order-grain input and removal of timedelta compatibility warnings.
- Expanded correctness and application checks; see docs/VERIFICATION.md for actual results.

The reference classification experiment is unchanged. Weak held-out performance is still disclosed; no scores were selected after seeing the test results.
