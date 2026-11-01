# Supply Chain Performance and Delivery Efficiency Analysis



- **Dataset Source:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce | Real 12,000-order sample

- **Generated At Utc:** 2026-11-01T15:28:41+00:00

- **Filters:** {}

- **Analytical Unit:** Distinct order

- **Metric Definitions:** Unit: distinct order. Eligible: delivered/completed with valid actual and promised duration. Durations: calendar days from order placement to customer delivery. Delay = actual - scheduled days; late > 0, on time <= 0. On-time rate = on-time eligible orders / eligible delivered orders. Same-calendar-day arrival is on time. Sales are aggregated once per order; currency is unspecified for uploads.

- **Eligible Population:** Delivered/completed orders with valid actual and scheduled delivery durations.

- **Limitations:** Historical observational data; associations are not causal. Cancelled, undelivered and unknown outcomes are excluded from delivery-rate denominators. Small groups are unstable. No measured savings, carrier quality, inventory efficiency or current service guarantees are inferred.



## Metrics



- total_orders: 12000

- eligible_orders: 11668

- excluded_orders: 332

- late_orders: 814

- on_time_orders: 10854

- on_time_rate: 0.9302365443949263

- late_rate: 0.0697634556050737

- mean_signed_delay: -11.853616729516627

- mean_late_delay: 11.518427518427519

- median_delivery_days: 10.0

- sales: 1640938.2200000002

- profit: Not available



## Findings



### RJ (region) deserves a closer look.

11.8% late across 1,521 eligible orders; 180 late orders; mean late-only delay 15.2 days.

Overall late rate 7.0%; difference 4.9 percentage points.

95% Wilson interval 10.3%–13.6%. This is descriptive uncertainty, not a significance test.

Action to consider: Review the promise lengths, destination mix and product composition before choosing an operational intervention.

Limitation: Observational associations do not establish causes. Historical orders may not represent current operations.



### CE (region) deserves a closer look.

17.3% late across 168 eligible orders; 29 late orders; mean late-only delay 16.2 days.

Overall late rate 7.0%; difference 10.3 percentage points.

95% Wilson interval 12.3%–23.7%. This is descriptive uncertainty, not a significance test.

Action to consider: Review the promise lengths, destination mix and product composition before choosing an operational intervention.

Limitation: Observational associations do not establish causes. Historical orders may not represent current operations.



### BA (region) deserves a closer look.

12.7% late across 386 eligible orders; 49 late orders; mean late-only delay 11.6 days.

Overall late rate 7.0%; difference 5.7 percentage points.

95% Wilson interval 9.7%–16.4%. This is descriptive uncertainty, not a significance test.

Action to consider: Review the promise lengths, destination mix and product composition before choosing an operational intervention.

Limitation: Observational associations do not establish causes. Historical orders may not represent current operations.



### PA (region) deserves a closer look.

13.9% late across 115 eligible orders; 16 late orders; mean late-only delay 23.6 days.

Overall late rate 7.0%; difference 6.9 percentage points.

95% Wilson interval 8.7%–21.4%. This is descriptive uncertainty, not a significance test.

Action to consider: Review the promise lengths, destination mix and product composition before choosing an operational intervention.

Limitation: Observational associations do not establish causes. Historical orders may not represent current operations.
