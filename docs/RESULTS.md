# Measured results

These are actual results from the included real Olist 12,000-order sample, not a claimed production benchmark.

Source: [Olist / Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Accessed 2026-11-01. Data/results: CC BY-NC-SA 4.0.

## Descriptive population

- **Total Orders:** 12000
- **Eligible Orders:** 11668
- **Excluded Orders:** 332
- **Late Orders:** 814
- **On Time Orders:** 10854
- **On Time Rate:** 93.02%
- **Mean Signed Delay:** -11.85 calendar days
- **Mean Late Delay:** 11.52 calendar days
- **Median Delivery Days:** 10.00 calendar days

See artifacts/data_quality.json for missing values and exclusion reasons. Descriptive figures use all usable sample orders; predictive split counts below differ because unresolved outcomes are excluded and cutoff purges remove late-known outcomes.

## Chronological periods

| Split | First order | Last order | Retained orders | Late orders | Late rate |
|---|---|---|---:|---:|---:|
| Train | 2016-10-04 | 2017-12-27 | 5,012 | 223 | 4.45% |
| Validation | 2018-01-01 | 2018-04-26 | 2,894 | 304 | 10.50% |
| Test | 2018-05-01 | 2018-08-29 | 3,036 | 126 | 4.15% |

Purged for label availability: 311 training orders and 415 validation orders. Label availability is delivery day + one day; actual administrative delays are unknown.

## Final untouched test results

| Model | Accuracy | Late precision | Late recall | Late F1 | ROC-AUC | PR-AUC/AP | Brier error | Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dummy baseline | 0.958 | 0.000 | 0.000 | 0.000 | 0.500 | 0.042 | 0.040 | 0.50 |
| Logistic Regression | 0.407 | 0.053 | 0.786 | 0.099 | 0.658 | 0.081 | 0.262 | 0.40 |
| Random Forest | 0.436 | 0.051 | 0.714 | 0.095 | 0.603 | 0.059 | 0.221 | 0.45 |

**Selected by validation: Random Forest, threshold 0.45.**

The test set contains 126 late orders. The selected model catches 90, misses 36, and raises 1,677 false late alarms. This is weak precision and should be presented as a limited educational experiment.

The majority-class dummy achieves high accuracy while catching no late orders. The selected model improves ranking over a constant probability but has substantially worse Brier error. Its balanced class weights and validation-selected threshold do not produce reliable operational probabilities on this later period.

Logistic Regression has better AP than the selected Random Forest on this particular test period. The model was not switched after seeing test results: selection used validation AP only. Validation late prevalence differs substantially from train/test, demonstrating temporal drift and the limitations of one historical split.

## Calibration and interpretation

The application shows six test quantile reliability bins and Brier score. No post-hoc calibration was fitted. Risk estimates are not guaranteed confidence. Coefficients belong to the Logistic Regression comparator and do not establish causal effects.

## Features and protocol

- Prediction moment: order placement, conditional on eventual observed delivery.
- Included: sales, quantity, scheduled_days, order_month, order_weekday, region, category.
- Preprocessing: train-only numeric imputation/scaling and categorical imputation/one-hot encoding.
- Selection: Highest validation average precision (AP); validation F1 tie-break. Threshold maximizes validation F1 over 0.05 to 0.80.

## Limitations

- Historical observational sample; performance can drift across time, states and products.
- Only orders with observed delivery outcomes are modeled; cancellation and non-delivery risk are outside the target.
- Label timing uses delivery day + 1 day; administrative reporting delays are unknown.
- Checkout availability of price, quantity, category and promise is assumed for Olist; confirm for uploaded data.
- F1 thresholds reflect a heuristic, not a measured business cost or guaranteed service improvement.
- Coefficients describe associations in the Logistic Regression comparator and are not causal effects.

No shipping-mode, profit, discount, inventory, carrier or savings result is inferred from absent fields. See METHODOLOGY.md and VERIFICATION.md for the protocol and executed checks.
