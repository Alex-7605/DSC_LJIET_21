# Five-minute demonstration — version 2
Before the exam, double-click Start Project.cmd. Click Start guided demo to restore the real sample and clear filters; use Next section to advance. Presentation mode keeps source controls compact.

## 0:00–0:40 — Overview

Introduce the title and real Olist sample. Explain “distinct order” and distinguish all selected orders from eligible delivered orders. Read the on-time rate and median order-to-customer-delivery time directly from the live page.

## 0:40–1:20 — Explore Data

Show rows loaded, usable orders, duplicate and invalid counts. Explain why cancellation and unknown arrival are excluded from delivery-rate denominators. Point out that source data remains separate from cleaned data.

## 1:20–2:00 — Delivery Performance

Open the region/state comparison. The bars show volume and the line shows late rate with a fixed percentage scale. Explain that a small group can have a high rate with weak evidence. Show the late-only and signed-delay distinction. Use a region filter, then clear it.

## 2:00–2:40 — Business Insights

Read one generated finding with its exact rate, count and overall baseline. Point out the Wilson interval, proposed investigation and alternative explanations. These are computed findings, not generated business facts or measured savings.

## 2:40–3:35 — Model Evaluation

On a fresh checkout, click Train and evaluate models once. Show the chronological dates and label-availability purge. Compare the dummy with Logistic Regression and Random Forest. Read precision, recall and AP from the actual held-out table. Explain why high accuracy can miss late deliveries.

## 3:35–4:20 — Predict Delivery Risk

Use default form values and select Estimate delivery risk. Explain the model, threshold, estimated probability and uncertainty. The estimate concerns late arrival among observed deliveries, not every possible failure. Changing a field does not prove a causal benefit.

## 4:20–5:00 — Reports and Project Guide

Download a filtered summary or insight report. Show provenance, definitions and limitations. Open the guide and explain the data-flow diagram: input → validation → order table → metrics/insights and a separate model branch.

Finish with: “The project demonstrates reliable measurement and honest model evaluation. Real operational changes would need more recent data and an independent validation study.”
## Optional CSV question from the examiner

Switch Dataset to Upload CSV and choose data/examples/general_example.csv. The file is explicitly synthetic. Show the schema/profile and Chart studio, then explain why this unrelated table has no inferred delivery target. Switch to the delivery template and explicitly map it to demonstrate the two paths. Use Start guided demo to return to the real Olist sample.