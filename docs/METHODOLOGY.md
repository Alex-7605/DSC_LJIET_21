# Methodology

## Research question and population

How often do observed delivered orders meet the checkout promise, where are late deliveries concentrated, and can placement-time attributes help estimate late risk?

The analytical unit is an order. Delivery-rate denominators contain only delivered/completed orders with usable actual and scheduled duration. Cancellation, unresolved delivery and unknown outcomes remain visible as excluded populations. The model consequently estimates **lateness conditional on eventual observed delivery**, not cancellation or total fulfillment failure.

## Reproducible data preparation

The real sample contains 12,000 orders sampled with seed 21 from the official Olist files. Product categories are translated using the provided translation table. Item-price values and item counts are aggregated to order level before joining to orders. Source and output SHA-256 hashes are recorded in data/sample/provenance.json.

Customer linkage and fine location fields are removed and order hashes replaced. The original ZIP remains local and ignored by Git. The distributed derivative retains the source's CC BY-NC-SA 4.0 conditions and attribution.

Uploads remain in session memory. File size, encoding, CSV structure, explicit date format, required fields, finite numbers, duplicate records, date ordering, duration sign and order consistency are checked. Invalid lines invalidate their whole order, avoiding understated partial totals. Valid outliers stay in the data.

## Shared metric definitions

- Actual duration: customer-arrival calendar date minus placement calendar date.
- Scheduled duration: promise calendar date minus placement calendar date.
- Signed delay: actual minus scheduled days.
- Late: signed delay > 0. On time: signed delay <= 0.
- On-time rate: on-time eligible orders / eligible delivered orders.
- Mean signed delay includes early and late deliveries.
- Mean late-only delay uses positive delays only.
- Median duration uses eligible order-to-delivery calendar days.
- Total distinct orders includes the usable excluded population.
- Goods value is the sum of order goods totals once each, excluding freight. Profit appears only for a supported uploaded field.

Same-day arrival is on time even when the estimated timestamp is midnight. This calendar-day interpretation is explicit and can differ from a strict timestamp-based target. No shipment timestamp is relabeled as customer arrival. Unknown denominators produce Not available.

## Exploration and evidence

Descriptive filters are applied centrally before metrics, charts, insights and analytical downloads. Rate charts carry volume, use a fixed 0–100% rate axis and select their top 10 by eligible volume. Monthly trends use order month. Correlations use selected numeric measures and pairwise complete eligible records, excluding identifiers and category codes.

Ranked findings require 30 eligible orders by default. Small groups remain in performance tables as Insufficient evidence. A 95% Wilson interval describes uncertainty in a group's late proportion; it is not a difference test and ignores temporal dependence and multiple comparisons.

Investigation priority = late count × max(group rate − overall rate, 0) × (1 + late-only mean delay / 7).
This is a transparent heuristic, not an optimization model. Groups overlap across dimensions and scores should not be added. Findings discuss alternative explanations such as different promises and product/destination mix. No measured savings or causal effects are claimed.

## Prediction moment and feature audit

Prediction takes place at order placement. Candidate features are goods value, quantity, scheduled days, placement month/weekday, destination state and product category. Optional supported shipping mode, segment and discount can join for uploads only after their availability is confirmed.

Actual duration/date, signed delay, final status, late label, supplied label, profit, order/item identifiers and all outcome administration are excluded by a strict feature allowlist. Product and financial availability at checkout is a semantic assumption for the historic Olist tables; there is no full event log to verify retrospective revisions.

Disagreement with a supplied late flag is shown and **blocks training**, rather than selecting the more favorable label.

## Chronological experiment

Use a fixed seed of 21. Split 60/20/20 of distinct order dates into train, validation and test. All orders from one calendar date remain together, and order-level aggregation prevents item leakage across splits.

Before fitting, purge train orders whose outcomes would not be known before validation starts, and purge validation orders whose outcomes would not be known before test starts. Label availability is approximated by delivery calendar date plus one day. For verified duration-only uploads it is placement date plus actual days plus one day. Source administrative reporting latency is unknown.

Require at least 300 eligible orders, 30 order dates, and 50 records with at least three examples of each class in each retained split. An unsupported setup is rejected while descriptive analytics remain usable.

Each model uses a Pipeline and ColumnTransformer: median numeric imputation and StandardScaler; most-frequent categorical imputation and one-hot encoding with unknown-category handling. Fit preprocessing on train only. Compare DummyClassifier(prior), Logistic Regression and Random Forest (120 trees, depth 10, minimum leaf 8). Balanced class weights are used when the minority share in train is below 20%.

Choose the learned model by validation average precision, with validation F1 as tie-breaker. Choose each learned classifier's threshold using validation F1 on the fixed grid 0.05–0.80 in steps of 0.05. The dummy retains 0.50. Do not refit after selection or alter the experiment using final test results.

## Evaluation and interpretation

Report class distribution, accuracy, positive-class precision/recall/F1, ROC-AUC, average precision (AP, labeled PR-AUC/AP), confusion matrix and Brier score. AP is a stepwise precision-recall summary, not trapezoidal area.

A model may have high accuracy by predicting the majority on-time class and miss late orders. Compare AP against the dummy and test prevalence; compare recall with the number of false alarms. F1 is a heuristic tradeoff, not an established business cost function.

Six quantile reliability bins and Brier score assess probability calibration on test. No post-hoc calibration is fitted. Risk values remain uncertain model estimates. Logistic coefficients explain associations in that comparator, not causal effects or individual Random Forest decisions.

Training happens only through the explicit button or scripts/train.py. A fingerprint includes validated data, feature/configuration schema, seed and scikit-learn version. Dataset changes invalidate session models; mismatched local artifacts are ignored. Only a fixed locally generated sample joblib path is loaded. Never upload or load an untrusted pickle/joblib.

## Limits and reproducibility

Historical Brazilian marketplace orders and a small sample do not establish present-day global performance. Train/test drift, survivor bias, missing outcomes, uncertain administrative reporting delays and category sparsity limit generalization. The project has no carrier IDs, shipping modes, profit, discounts, customer segments, inventory levels, distance or measured savings in its real sample.

See artifacts/model_evaluation.json for exact measured results and splits, docs/RESULTS.md for readable results, and docs/VERIFICATION.md for checks actually performed.