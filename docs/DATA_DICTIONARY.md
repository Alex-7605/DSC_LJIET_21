# Data dictionary

Analytical grain: **one row per distinct order**. Original customer identifiers, cities, postal codes, seller IDs, review text, exact locations and customer linkage are absent from the distributed sample.

## Olist source-to-analytical mapping

| Analytical field | Original source | Meaning and unit | Missing handling |
|---|---|---|---|
| order_id | orders.order_id | Replaced by OLIST-000001 style IDs; used only for grouping | Missing IDs excluded |
| order_date | order_purchase_timestamp | Placement timestamp; timezone unspecified in source | Missing/invalid excluded |
| delivery_date | order_delivered_customer_date | Actual customer arrival, never carrier handover | Not eligible when absent |
| promised_date | order_estimated_delivery_date | Estimated date shown to customer; calendar-day promise | Not eligible when absent |
| status | order_status | delivered, shipped, canceled and other statuses | Unknown is not eligible |
| region | customers.customer_state | Brazilian destination state abbreviation | Unknown retained |
| category | products + translation | English category; Mixed if several; Unknown if unavailable | Unknown retained |
| sales | items.price aggregated by order | Sum of goods price; excludes freight; source monetary units | Missing remains missing |
| quantity | count(items.order_item_id) | Number of purchased item records | Missing remains missing |

The original item table is aggregated **before** joining to orders. An order with three items still contributes one delivery outcome. The application does not assume a currency without an explicit source declaration.

## Derived fields

| Field | Definition |
|---|---|
| actual_days | delivery calendar date − order calendar date |
| scheduled_days | promised calendar date − order calendar date |
| delay_days | actual_days − scheduled_days |
| eligible | Delivered/completed status and valid actual/scheduled durations |
| late | 1 if eligible and delay > 0; 0 otherwise; missing for excluded outcomes |
| delivery_outcome | On time, Late, or Excluded / unknown |
| exclusion_reason | Cancelled, undelivered/unknown, or missing outcome |
| label_mismatch | Supplied binary label disagrees with derived eligible target |
| order_month | Order month 1–12 |
| order_weekday | Order weekday 0–6 (Monday = 0) |

## Optional upload fields

The mapping UI supports shipping_mode, segment, discount (fraction 0–1), profit, verified actual_days/scheduled_days, supplied_late, and item_id. These fields are absent from the Olist sample and are never invented. Item-level uploads require an item identifier so valid identical products are not mistaken for duplicated lines. Item IDs need be unique only within an order.

Choose ISO8601 or an explicit day/month format. Ambiguous dates do not silently receive a locale. ISO mode accepts timezone-naive YYYY-MM-DD with optional time. Normalize timezone-bearing source dates before upload.

The uploader suggests exact known aliases, such as Order ID, Order Date, customer_state and Shipping Mode. Multiple candidates remain unmapped until you choose. DataCo's actual shipping duration is deliberately not assumed to mean customer arrival.

## Aggregation and missing values

Choose order/item input grain and order/item financial grain explicitly. Exact rows are removed; repeated order IDs are never removed merely for repeating. Order-grain nonidentical repetitions are conflicts. Item-grain order dates, statuses, promises, destination and delivery outcomes must agree; otherwise the entire order is excluded. Conflicting item identifiers also exclude the order.

Line-level sales, profit and quantity are summed. Repeated order totals must agree and are retained once. A missing item value makes its order total unknown instead of producing an understated total. Multi-category orders become Mixed. Mixed line discounts become unknown. Legitimate large durations and negative profit are retained; negative durations, negative sales, nonpositive/noninteger quantity and invalid discount fractions are invalid.

Models impute numeric/categorical predictor gaps inside training-only pipelines. Delivery outcomes and target labels are never imputed.