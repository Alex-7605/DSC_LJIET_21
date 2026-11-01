# Viva guide

## Thirty-second introduction

“My project analyzes supply chain delivery performance using real Olist e-commerce orders. It validates data, measures on-time delivery at order level, compares destinations and product categories, and generates numerical investigation priorities. It also compares a dummy baseline, Logistic Regression and Random Forest using later orders as the test set. The dashboard explains uncertainty and avoids using delivery outcomes as prediction inputs.”

## Problem statement

A business can see many orders and still struggle to identify where late delivery is concentrated. This project provides consistent metrics, group comparisons, transparent evidence and a limited predictive experiment. It does not claim to optimize the whole supply chain.

## Technology choices

Python keeps the data science and application in one readable project. Pandas handles tables, NumPy supports numeric operations, Plotly provides interactive charts, Streamlit gives a local website, and scikit-learn provides tested preprocessing and classifiers. Pytest checks important calculations and failure cases.

## Twenty-two likely questions

1. **What is the analytical grain?** One row per distinct order. Item values are aggregated before joining so delivery outcomes and order totals are not multiplied.
2. **Where did the data come from?** The official Olist Brazilian E-Commerce dataset on Kaggle. A reproducible 12,000-order real sample is included with attribution and its non-commercial share-alike license.
3. **Why Olist instead of DataCo?** Olist explicitly distinguishes actual customer delivery from carrier handover and includes an estimated delivery date, supporting arrival-based metrics.
4. **How is late delivery defined?** The customer receives the order on a later calendar date than the checkout promise.
5. **What counts as on time?** Eligible delivery on or before the promised calendar date.
6. **Do cancelled orders count as late?** No. Cancelled, undelivered and unknown outcomes are shown separately and excluded from the rate denominator.
7. **What is the target?** Binary late flag, 1 for late and 0 for on time, among eligible delivered orders.
8. **When is the prediction made?** At order placement. Only fields expected to be known then are candidates.
9. **What is data leakage?** Information unavailable at prediction time helps the model unfairly. Actual duration, final status and delay are excluded.
10. **Why avoid a random row split?** Items from the same order could leak across sets, and future information could appear in training. We aggregate by order and use chronological periods.
11. **What is the label-availability purge?** Orders delivered too close to a cutoff are removed from the earlier split because their outcomes would not yet be known.
12. **Why use a dummy model?** It shows what simple class-prior prediction can achieve without learning meaningful relationships.
13. **Why Logistic Regression?** It is a readable classification baseline with interpretable log-odds coefficients.
14. **Why Random Forest?** It can learn nonlinear patterns and feature interactions, with modest depth and leaf limits to constrain complexity.
15. **What is overfitting?** Learning training-specific patterns that fail on new orders. Held-out later periods help reveal it.
16. **Precision versus recall?** Precision asks what fraction of flagged orders are actually late. Recall asks what fraction of all late orders were flagged.
17. **Why can accuracy mislead?** When late orders are rare, predicting everything on time can have high accuracy but zero late recall.
18. **What is PR-AUC here?** Average precision summarizes precision-recall performance across thresholds. It is especially useful with rare late outcomes.
19. **How is the threshold chosen?** Maximize validation F1 on a fixed small grid, never using the final test labels.
20. **Is 70% risk guaranteed confidence?** No. It is a model estimate. Reliability bins and Brier score assess probability quality, and drift can change it.
21. **Does a high group late rate prove the group causes delays?** No. Different promises, routes and product mixes can explain the association. Correlation is not causation.
22. **What should improve next?** Obtain current audited delivery events, confirm feature timing, assess fairness and drift, use business-defined error costs, and validate in a prospective trial.

## Explain weak results honestly

Use the actual table in docs/RESULTS.md or Model Evaluation. Explain the selected model's recall, precision and AP against the dummy. Say plainly if gains are small or calibration is poor. Do not describe a high accuracy score as proof of operational value.

## Realistic future work

Larger contemporary samples, audited feature availability, repeated forward validation, temporal calibration, better uncertainty estimates, and operational feedback could strengthen the project. A real intervention would require a separate causal or prospective evaluation before reporting savings.