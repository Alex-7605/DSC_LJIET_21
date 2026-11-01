"""Deterministic findings with denominators, uncertainty and actionable caveats."""
from src.metrics import group_performance, kpis

def build_insights(orders, minimum=30, limit=4):
    baseline = kpis(orders)
    if not baseline["eligible_orders"]:
        return []
    findings = []
    for column in ["region", "category", "shipping_mode", "segment"]:
        if column not in orders:
            continue
        table = group_performance(orders, column, minimum)
        for _, row in table.iterrows():
            if row.evidence != "Sufficient" or row[column] in {"Unknown", "Mixed"}:
                continue
            excess = row.late_rate - baseline["late_rate"]
            if excess <= 0:
                continue
            severity = row.mean_late_delay or 0
            priority = row.late_orders * excess * (1 + severity / 7)
            findings.append({
                "finding": f"{row[column]} ({column}) deserves a closer look.",
                "evidence": f"{row.late_rate:.1%} late across {int(row.eligible_orders):,} eligible orders; {int(row.late_orders):,} late orders; mean late-only delay {severity:.1f} days.",
                "baseline": f"Overall late rate {baseline['late_rate']:.1%}; difference {excess*100:.1f} percentage points.",
                "uncertainty": f"95% Wilson interval {row.ci_low:.1%}–{row.ci_high:.1%}. This is descriptive uncertainty, not a significance test.",
                "action": "Review the promise lengths, destination mix and product composition before choosing an operational intervention.",
                "limitation": "Observational associations do not establish causes. Historical orders may not represent current operations.",
                "priority_score": float(priority), "group": str(row[column]),
                "eligible_orders": int(row.eligible_orders), "late_rate": float(row.late_rate),
            })
    return sorted(findings, key=lambda item: item["priority_score"], reverse=True)[:limit]