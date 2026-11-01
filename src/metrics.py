"""Central metric definitions, always at one row per distinct order."""
from math import sqrt
import pandas as pd

DEFINITIONS = (
    "Unit: distinct order. Eligible: delivered/completed with valid actual and promised duration. "
    "Durations: calendar days from order placement to customer delivery. "
    "Delay = actual - scheduled days; late > 0, on time <= 0. "
    "On-time rate = on-time eligible orders / eligible delivered orders. "
    "Same-calendar-day arrival is on time. Sales are aggregated once per order; currency is unspecified for uploads."
)

def kpis(orders):
    eligible = orders.loc[orders.eligible]
    late = eligible.loc[eligible.late.eq(1)]
    n = len(eligible)
    return {
        "total_orders": len(orders), "eligible_orders": n,
        "excluded_orders": len(orders) - n, "late_orders": len(late),
        "on_time_orders": n - len(late),
        "on_time_rate": (n - len(late)) / n if n else None,
        "late_rate": len(late) / n if n else None,
        "mean_signed_delay": float(eligible.delay_days.mean()) if n else None,
        "mean_late_delay": float(late.delay_days.mean()) if len(late) else None,
        "median_delivery_days": float(eligible.actual_days.median()) if n else None,
        "sales": float(orders.sales.sum(min_count=1)) if "sales" in orders and orders.sales.notna().any() else None,
        "profit": float(orders.profit.sum(min_count=1)) if "profit" in orders and orders.profit.notna().any() else None,
    }

def wilson_interval(successes, n, z=1.96):
    if n == 0:
        return None, None
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z*z/(2*n)) / denominator
    margin = z * sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return max(0., center-margin), min(1., center+margin)

def group_performance(orders, column, minimum=30):
    records = []
    for name, group in orders.groupby(column, observed=True, dropna=False):
        values = kpis(group)
        low, high = wilson_interval(values["late_orders"], values["eligible_orders"])
        records.append({column: name, **values, "ci_low": low, "ci_high": high,
                        "evidence": "Sufficient" if values["eligible_orders"] >= minimum else "Insufficient evidence"})
    return pd.DataFrame(records)

def monthly_performance(orders):
    if orders.empty:
        return pd.DataFrame()
    return group_performance(orders.assign(month=orders.order_date.dt.to_period("M").astype(str)), "month", minimum=1)