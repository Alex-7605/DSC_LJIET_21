"""Consistent Plotly styling; identifiers never enter numeric correlations."""
import plotly.express as px
import plotly.graph_objects as go
from src.metrics import group_performance, monthly_performance

NAVY, TEAL, RED = "#16324F", "#147D92", "#B91C1C"

def style(fig, title=None):
    fig.update_layout(title=title, template="plotly_white", paper_bgcolor="white",
                      plot_bgcolor="white", font={"family": "Arial", "color": "#1F2937"}, title_font_size=16,
                      colorway=[TEAL, NAVY, RED, "#B45309"], margin=dict(l=20, r=20, t=55, b=35),
                      legend_title_text="", hoverlabel=dict(bgcolor="white"), height=360)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EDF1F7", zeroline=True)
    return fig

def outcome_chart(orders):
    counts = orders.loc[orders.eligible, "delivery_outcome"].value_counts().rename_axis("Outcome").reset_index(name="Orders")
    return style(px.pie(counts, names="Outcome", values="Orders", hole=.72,
                        color="Outcome", color_discrete_map={"On time": TEAL, "Late": RED}), "Eligible delivery outcomes")

def group_chart(orders, column, minimum=30, top_n=10):
    table = group_performance(orders, column, minimum)
    table = table.sort_values("eligible_orders", ascending=False).head(top_n)
    fig = go.Figure()
    fig.add_bar(x=table[column], y=table.eligible_orders, name="Eligible orders",
                marker_color="#DAE9EF", yaxis="y", hovertemplate="%{x}<br>%{y:,} eligible orders<extra></extra>")
    fig.add_scatter(x=table[column], y=table.late_rate*100, name="Late rate (%)",
                    mode="lines+markers", yaxis="y2", line=dict(color=RED),
                    customdata=table[["late_orders", "eligible_orders", "evidence"]].values,
                    hovertemplate="%{x}<br>Late %{y:.1f}%<br>%{customdata[0]} / %{customdata[1]}<br>%{customdata[2]}<extra></extra>")
    style(fig, f"Late rate & volume · {column.replace('_', ' ')}")
    fig.update_layout(yaxis=dict(title="Eligible orders", rangemode="tozero"),
                      yaxis2=dict(title="Late rate (%)", overlaying="y", side="right", range=[0, 100], tickmode="linear", dtick=20),
                      legend=dict(orientation="h", y=-.25), margin=dict(l=45,r=45,t=70,b=85))
    return fig, table

def trend_chart(orders):
    table = monthly_performance(orders)
    fig = px.line(table, x="month", y="on_time_rate", markers=True,
                  custom_data=["eligible_orders", "late_orders"])
    fig.update_traces(hovertemplate="%{x}<br>On time %{y:.1%}<br>%{customdata[0]} eligible orders<extra></extra>")
    style(fig, "Monthly on-time delivery · order month")
    fig.update_yaxes(range=[0, 1], tickformat=".0%", title="On-time rate")
    fig.update_xaxes(title="")
    return fig

def distribution(orders, column, title):
    data = orders.loc[orders.eligible]
    fig = px.histogram(data, x=column, nbins=40, color_discrete_sequence=[TEAL])
    style(fig, title)
    fig.update_xaxes(title="Calendar days")
    fig.update_yaxes(title="Eligible orders")
    return fig

def correlation_chart(orders):
    cols = [c for c in ["sales", "profit", "discount", "quantity", "scheduled_days", "actual_days", "delay_days"] if c in orders and orders[c].nunique() > 1]
    if len(cols) < 2:
        return None
    return style(px.imshow(orders.loc[orders.eligible, cols].corr(), zmin=-1, zmax=1,
                           color_continuous_scale="RdBu", text_auto=".2f"), "Numeric relationships · Pearson correlation")