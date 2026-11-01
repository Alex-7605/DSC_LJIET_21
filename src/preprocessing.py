"""One filter function for all descriptive pages and exports."""
import pandas as pd

def filter_orders(orders, filters):
    result = orders.copy()
    if filters.get("start"):
        result = result.loc[result.order_date.dt.date >= pd.Timestamp(filters["start"]).date()]
    if filters.get("end"):
        result = result.loc[result.order_date.dt.date <= pd.Timestamp(filters["end"]).date()]
    for col in ["region", "category", "shipping_mode", "segment", "delivery_outcome"]:
        if filters.get(col):
            result = result.loc[result[col].isin(filters[col])]
    return result