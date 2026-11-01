# Data flow and system design

The external entities are the student/analyst and the official Olist source. Data stores are local CSV files, session memory, and explicitly generated trusted model files. No database or external inference service is required.

## Level 0 — context diagram

```mermaid
flowchart LR
    O[Olist / Kaggle] -->|Licensed CSV sample| S((Supply Chain Analysis))
    U[Student / Analyst] -->|CSV, mappings, filters, prediction inputs| S
    S -->|Metrics, charts, evidence and risk estimates| U
    S -->|CSV / Markdown / evaluation downloads| U
```

## Level 1 — analytical data flow

```mermaid
flowchart TD
    A[Official Olist ZIP] --> B[prepare_data.py]
    B -->|Aggregate items; remove customer linkage; seed 21 sample| C[(Real order-level sample)]
    D[Uploaded CSV] --> E[Size, encoding and structure checks]
    E --> F[Explicit column mapping and date format]
    C --> G[Validation and order aggregation]
    F --> G
    E --> W[General CSV workspace]
    W --> Y[Conservative types and privacy exclusions]
    Y --> Z[Search, filters, supported charts and export bundle]
    G --> H[(Clean orders in session memory)]
    G --> Q[Quality and exclusion summary]
    H --> I[Shared filters]
    I --> J[Central metric functions]
    J --> K[Charts and deterministic insights]
    I --> L[Provenance-aware report exports]
    H --> M[Feature allowlist and temporal split]
    M --> N[Train-only preprocessing pipelines]
    N --> V[Validation model and threshold selection]
    V --> T[Final test evaluation]
    T --> P[Session model / trusted local sample artifact]
    U[New pre-delivery inputs] --> R[Input and training-range validation]
    P --> R
    R --> X[Manual / batch risk estimates]
```

Dashboard filters affect descriptive analysis and its downloads. The model branch deliberately uses the full validated dataset and a fixed chronological holdout.

## Model lifecycle

```mermaid
stateDiagram-v2
    [*] --> NoModel
    NoModel --> Training: Explicit button or train.py
    Training --> Ready: Successful temporal evaluation
    Training --> NoModel: Invalid setup / insufficient data
    Ready --> Ready: Filter or page change
    Ready --> NoModel: Dataset or schema fingerprint changes
    NoModel --> Ready: Matching trusted local sample artifact
```

## Modules

| Module | Responsibility |
|---|---|
| app.py | Local Streamlit navigation, forms, state and page layout |
| data_loader.py | Bounded CSV input, unambiguous alias suggestions, field allowlist |
| validation.py | Explicit dates, quality checks, item-to-order aggregation, eligibility |
| preprocessing.py | Shared descriptive filters |
| metrics.py | KPI definitions, grouped statistics and Wilson intervals |
| insights.py | Evidence-backed findings and heuristic investigation ranking |
| visualizations.py | Plotly charts with shared visual styling |
| modeling.py | Feature audit, purged chronological splits, pipelines and predictions |
| reporting.py | Consistent provenance-aware downloads and formula-safe CSVs |

See [the static diagram](assets/data-flow.svg) for a portable rendering.
## Version 2 route selection

General CSV exploration does not require order fields. Only an explicit delivery mapping enters the order-validation/model branch. Both routes preserve source bytes, bound file/table size and keep user uploads in session memory. Delimiter, encoding, header and numeric-format choices appear in the import workflow.

The general route uses source-row grain and separate provenance-aware ZIP exports. The delivery route retains its eligible-order metric definitions and fixed temporal model evaluation. Neither route silently turns an arbitrary numeric column into a late-delivery target.