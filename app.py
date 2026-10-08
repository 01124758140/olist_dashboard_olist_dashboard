"""
Olist dashboard  -  Dash + Plotly
Local run : python app.py            then open http://127.0.0.1:8050
Production: gunicorn app:server      (see Procfile / render.yaml)
Input     : data/olist_features.csv.gz  (or data/olist_features.csv)
            one row per order, produced by the Feature Engineering notebook step.
"""
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from dash import Dash, dcc, html, Input, Output
from plotly.subplots import make_subplots

# ---------------------------------------------------------------- data
BASE_DIR = Path(__file__).resolve().parent
CANDIDATES = [
    Path(os.environ["OLIST_DATA"]) if os.environ.get("OLIST_DATA") else None,
    BASE_DIR / "data" / "olist_features.csv.gz",
    BASE_DIR / "data" / "olist_features.csv",
]
PATH = next((p for p in CANDIDATES if p is not None and p.exists()), None)
if PATH is None:
    raise FileNotFoundError(
        "Data file not found. Put olist_features.csv (or olist_features.csv.gz) inside the "
        "'data' folder, or run: python prepare_data.py <path to olist_features.csv>")

# only the columns the dashboard really uses (keeps memory low on free hosting tiers)
USECOLS = [
    "order_id", "customer_unique_id", "customer_state", "order_status",
    "purchase_ts", "delivered_ts", "estimated_ts",
    "main_category", "payment_type", "installments",
    "n_items", "total_price", "total_freight", "order_value",
    "delivery_days", "delay_days", "is_late", "distance_km", "is_same_state",
    "review_score", "is_bad_review", "is_repeat_customer",
]

df = pd.read_csv(PATH, usecols=USECOLS, parse_dates=["purchase_ts", "delivered_ts", "estimated_ts"])
df = df[~df["order_status"].isin(["canceled", "unavailable"])].copy()   # revenue = real sales only
df["main_category"] = df["main_category"].fillna("unknown")
df["date"] = df["purchase_ts"].dt.normalize()
df["month"] = df["purchase_ts"].dt.to_period("M").dt.to_timestamp()
df["weekday"] = df["purchase_ts"].dt.day_name()
df["hour"] = df["purchase_ts"].dt.hour
df["delay_bucket"] = pd.cut(df["delay_days"], [-999, 0, 3, 7, 14, 999],
                            labels=["On time / early", "1-3 d late", "4-7 d late",
                                    "8-14 d late", "14+ d late"])
df["dist_bucket"] = pd.cut(df["distance_km"], [-1, 100, 300, 700, 1500, 1e6],
                           labels=["<100", "100-300", "300-700", "700-1500", "1500+"])
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ---------------------------------------------------------------- style
INK, TEAL, AMBER, SLATE, RED = "#16232B", "#0F6B73", "#D9902F", "#5B6B77", "#B23A48"
BG, PANEL, LINE = "#EEF1F3", "#FFFFFF", "#D7DDE1"
GROUP_COLOR = {"Sales": TEAL, "Delivery and service": AMBER, "Customers": SLATE}
FONT = "'IBM Plex Sans', 'Segoe UI', Tahoma, sans-serif"

CARDS = [  # (label, group)
    ("Revenue", "Sales"), ("Orders", "Sales"), ("Avg order value", "Sales"),
    ("Items per order", "Sales"), ("Freight paid", "Sales"),
    ("Freight share of order", "Sales"), ("Avg installments", "Sales"),
    ("Avg delivery time", "Delivery and service"), ("Late deliveries", "Delivery and service"),
    ("Avg seller distance", "Delivery and service"), ("Same-state orders", "Delivery and service"),
    ("Avg review score", "Delivery and service"), ("Bad reviews (1-2 stars)", "Delivery and service"),
    ("Unique customers", "Customers"), ("Repeat customers", "Customers"),
]
CHART_TITLES = [
    "Monthly revenue", "Monthly orders", "Top 10 categories by revenue",
    "Category share of revenue", "Top 10 states by revenue", "Payment methods",
    "Orders by weekday", "When customers buy (weekday x hour)", "Review score distribution",
    "Review score by delivery delay", "Delivery time by state (top 10 by orders)",
    "Distance: freight cost and late rate", "Order value distribution",
    "Installments vs order value", "Price vs freight (sample)",
]

# ---------------------------------------------------------------- layout
def card(i, label, group):
    return html.Div([
        html.Div(label, style={"fontSize": "13px", "color": SLATE}),
        html.Div(id=f"k{i}", style={"fontSize": "26px", "fontWeight": 600, "color": INK, "marginTop": "4px"}),
    ], style={"background": PANEL, "padding": "12px 14px", "borderRadius": "4px",
              "borderLeft": f"5px solid {GROUP_COLOR[group]}", "border": f"1px solid {LINE}",
              "borderLeftWidth": "5px", "borderLeftColor": GROUP_COLOR[group]})

def box(label, control):
    return html.Div([html.Div(label, style={"fontSize": "12px", "color": SLATE, "marginBottom": "4px"}), control],
                    style={"minWidth": "200px", "flex": "1"})

DATE_MIN, DATE_MAX = df["date"].min().date().isoformat(), df["date"].max().date().isoformat()
states = sorted(df["customer_state"].dropna().unique())
cats = sorted(df["main_category"].unique())
pays = sorted(df["payment_type"].dropna().unique())

app = Dash(__name__, title="Olist sales dashboard", external_stylesheets=[
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap"])

server = app.server          # gunicorn entry point:  gunicorn app:server

app.layout = html.Div(style={"background": BG, "minHeight": "100vh", "fontFamily": FONT, "color": INK}, children=[
    html.Div([
        html.H1("Olist marketplace performance", style={"margin": 0, "fontSize": "26px"}),
        html.Div("Brazilian e-commerce orders, Sep 2016 to Sep 2018. Canceled and unavailable orders are excluded.",
                 style={"color": "#C9D3D9", "marginTop": "4px", "fontSize": "14px"}),
    ], style={"background": INK, "color": "white", "padding": "20px 28px"}),

    # filters: they drive every card and chart
    html.Div([
        box("Purchase date", dcc.DatePickerRange(id="f_date", start_date=DATE_MIN, end_date=DATE_MAX,
                                                  min_date_allowed=DATE_MIN, max_date_allowed=DATE_MAX)),
        box("Customer state", dcc.Dropdown(states, multi=True, id="f_state", placeholder="All states")),
        box("Product category", dcc.Dropdown(cats, multi=True, id="f_cat", placeholder="All categories")),
        box("Payment method", dcc.Dropdown(pays, multi=True, id="f_pay", placeholder="All methods")),
        box("Delivery", dcc.RadioItems(
            [{"label": " All", "value": "all"}, {"label": " Late", "value": "late"}, {"label": " On time", "value": "ontime"}],
            "all", id="f_late", inline=True, inputStyle={"marginLeft": "10px"})),
    ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "padding": "14px 28px", "background": PANEL,
              "borderBottom": f"1px solid {LINE}", "position": "sticky", "top": 0, "zIndex": 10}),

    html.Div([
        html.Div([card(i, l, g) for i, (l, g) in enumerate(CARDS)],
                 style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(190px, 1fr))", "gap": "12px"}),
        html.Div([html.Div(dcc.Graph(id=f"g{i}", config={"displayModeBar": False}, style={"height": "340px"}),
                           style={"background": PANEL, "border": f"1px solid {LINE}", "borderRadius": "4px", "padding": "6px"})
                  for i in range(15)],
                 style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(480px, 1fr))",
                        "gap": "12px", "marginTop": "16px"}),
    ], style={"padding": "18px 28px 40px"}),
])

# ---------------------------------------------------------------- helpers
def style(fig, title, legend=False):
    fig.update_layout(title=dict(text=title, font=dict(size=15, color=INK), x=0.02), template="plotly_white",
                      margin=dict(l=40, r=15, t=48, b=35), showlegend=legend, font=dict(family=FONT, color=INK),
                      paper_bgcolor=PANEL, plot_bgcolor=PANEL)
    return fig

def empty(i):
    fig = go.Figure()
    fig.add_annotation(text="No orders match these filters", showarrow=False, font=dict(size=14, color=SLATE))
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return style(fig, CHART_TITLES[i])

def fmt(v, pattern):
    return "-" if pd.isna(v) else pattern.format(v)

# ---------------------------------------------------------------- callback
@app.callback([Output(f"k{i}", "children") for i in range(15)] + [Output(f"g{i}", "figure") for i in range(15)],
              Input("f_date", "start_date"), Input("f_date", "end_date"), Input("f_state", "value"),
              Input("f_cat", "value"), Input("f_pay", "value"), Input("f_late", "value"))
def update(start, end, st, ct, pay, late):
    d = df[(df["date"] >= start) & (df["date"] <= end)]
    if st:  d = d[d["customer_state"].isin(st)]
    if ct:  d = d[d["main_category"].isin(ct)]
    if pay: d = d[d["payment_type"].isin(pay)]
    if late == "late":     d = d[d["is_late"] == 1]
    elif late == "ontime": d = d[d["is_late"] == 0]
    if d.empty:
        return ["-"] * 15 + [empty(i) for i in range(15)]

    # ---- 15 cards
    kpis = [
        fmt(d["total_price"].sum(), "R$ {:,.0f}"), f"{len(d):,}", fmt(d["total_price"].mean(), "R$ {:,.1f}"),
        fmt(d["n_items"].mean(), "{:.2f}"), fmt(d["total_freight"].sum(), "R$ {:,.0f}"),
        fmt(d["total_freight"].sum() / d["order_value"].sum() * 100, "{:.1f}%"), fmt(d["installments"].mean(), "{:.1f}"),
        fmt(d["delivery_days"].mean(), "{:.1f} days"), fmt(d["is_late"].mean() * 100, "{:.1f}%"),
        fmt(d["distance_km"].mean(), "{:,.0f} km"), fmt(d["is_same_state"].mean() * 100, "{:.1f}%"),
        fmt(d["review_score"].mean(), "{:.2f} / 5"), fmt(d["is_bad_review"].mean() * 100, "{:.1f}%"),
        f"{d['customer_unique_id'].nunique():,}",
        fmt(d.drop_duplicates("customer_unique_id")["is_repeat_customer"].mean() * 100, "{:.1f}%"),
    ]

    figs = []
    # 1 monthly revenue: trend over time -> area line
    m = d.groupby("month")["total_price"].sum().reset_index()
    f = px.area(m, x="month", y="total_price", color_discrete_sequence=[TEAL])
    figs.append(style(f, CHART_TITLES[0]).update_yaxes(title=None).update_xaxes(title=None))
    # 2 monthly orders: counts per period -> columns
    m = d.groupby("month")["order_id"].count().reset_index()
    f = px.bar(m, x="month", y="order_id", color_discrete_sequence=[SLATE])
    figs.append(style(f, CHART_TITLES[1]).update_yaxes(title=None).update_xaxes(title=None))
    # 3 top categories: ranked comparison -> horizontal bars
    c = d.groupby("main_category")["total_price"].sum().nlargest(10).sort_values()
    f = px.bar(x=c.values, y=c.index, orientation="h", color_discrete_sequence=[TEAL])
    figs.append(style(f, CHART_TITLES[2]).update_xaxes(title=None).update_yaxes(title=None))
    # 4 category share: part-to-whole with many parts -> treemap
    c = d.groupby("main_category")["total_price"].sum().nlargest(20).reset_index()
    f = px.treemap(c, path=["main_category"], values="total_price", color="total_price",
                   color_continuous_scale=["#CFE3E5", TEAL])
    f.update_coloraxes(showscale=False)
    figs.append(style(f, CHART_TITLES[3]))
    # 5 top states: ranked comparison -> columns
    s = d.groupby("customer_state")["total_price"].sum().nlargest(10).reset_index()
    f = px.bar(s, x="customer_state", y="total_price", color_discrete_sequence=[TEAL])
    figs.append(style(f, CHART_TITLES[4]).update_yaxes(title=None).update_xaxes(title=None))
    # 6 payment methods: few parts of a whole -> donut
    p = d["payment_type"].value_counts().reset_index()
    f = px.pie(p, names="payment_type", values="count", hole=0.55,
               color_discrete_sequence=[TEAL, AMBER, SLATE, RED, "#9DB4BC"])
    figs.append(style(f, CHART_TITLES[5], legend=True))
    # 7 weekday: ordered categories -> columns
    w = d["weekday"].value_counts().reindex(DAYS).fillna(0)
    f = px.bar(x=w.index, y=w.values, color_discrete_sequence=[AMBER])
    figs.append(style(f, CHART_TITLES[6]).update_yaxes(title=None).update_xaxes(title=None))
    # 8 weekday x hour: two categorical dimensions -> heatmap
    h = d.pivot_table(index="weekday", columns="hour", values="order_id", aggfunc="count").reindex(DAYS)
    f = go.Figure(go.Heatmap(z=h.values, x=h.columns, y=h.index, colorscale=["#EEF6F7", TEAL], showscale=False))
    f.update_yaxes(autorange="reversed")
    figs.append(style(f, CHART_TITLES[7]))
    # 9 review scores: distribution of a 1-5 rating -> columns
    r = d["review_score"].round().value_counts().sort_index()
    f = px.bar(x=r.index.astype(int).astype(str), y=r.values, color=r.index.astype(int).astype(str),
               color_discrete_map={"1": RED, "2": "#D9743A", "3": AMBER, "4": "#6FA3A9", "5": TEAL})
    figs.append(style(f, CHART_TITLES[8]).update_yaxes(title=None).update_xaxes(title="Stars"))
    # 10 delay vs review: ordered buckets, single measure -> columns
    b = d.groupby("delay_bucket", observed=True)["review_score"].mean().reset_index()
    f = px.bar(b, x="delay_bucket", y="review_score", color_discrete_sequence=[RED])
    figs.append(style(f, CHART_TITLES[9]).update_yaxes(title="Avg stars", range=[1, 5]).update_xaxes(title=None))
    # 11 delivery time by state: ranked values with long labels -> horizontal bars
    top = d["customer_state"].value_counts().nlargest(10).index
    t = d[d["customer_state"].isin(top)].groupby("customer_state")["delivery_days"].mean().sort_values()
    f = px.bar(x=t.values, y=t.index, orientation="h", color_discrete_sequence=[AMBER])
    figs.append(style(f, CHART_TITLES[10]).update_xaxes(title="Days").update_yaxes(title=None))
    # 12 distance: two measures on one axis of buckets -> columns + line
    g = d.groupby("dist_bucket", observed=True).agg(freight=("total_freight", "mean"), late=("is_late", "mean")).reset_index()
    f = make_subplots(specs=[[{"secondary_y": True}]])
    f.add_bar(x=g["dist_bucket"].astype(str), y=g["freight"], name="Avg freight (R$)", marker_color=SLATE)
    f.add_scatter(x=g["dist_bucket"].astype(str), y=g["late"] * 100, name="Late %", mode="lines+markers",
                  line=dict(color=RED), secondary_y=True)
    f.update_xaxes(title="Distance (km)")
    figs.append(style(f, CHART_TITLES[11], legend=True).update_layout(legend=dict(orientation="h", y=-0.3)))
    # 13 order value: shape of one numeric variable -> histogram (capped at the 99th percentile)
    cap = d["total_price"].quantile(0.99)
    f = px.histogram(d[d["total_price"] <= cap], x="total_price", nbins=50, color_discrete_sequence=[TEAL])
    figs.append(style(f, CHART_TITLES[12]).update_yaxes(title=None).update_xaxes(title="Order value (R$)"))
    # 14 installments: numeric steps vs average -> columns (steps with 30+ orders, up to 12)
    i = d.groupby("installments")["total_price"].agg(["mean", "count"])
    i = i[(i["count"] >= 30) & (i.index <= 12)].reset_index()
    f = px.bar(i, x="installments", y="mean", color_discrete_sequence=[AMBER])
    figs.append(style(f, CHART_TITLES[13]).update_yaxes(title="Avg order value (R$)").update_xaxes(title="Installments", dtick=1))
    # 15 price vs freight: relationship of two numbers -> scatter on a random sample
    s = d.sample(min(4000, len(d)), random_state=1).copy()
    s["delivery"] = s["is_late"].map({0.0: "On time", 1.0: "Late"}).fillna("Not delivered")
    f = px.scatter(s, x="total_price", y="total_freight", color="delivery", opacity=0.5, log_x=True,
                   color_discrete_map={"On time": TEAL, "Late": RED, "Not delivered": "#9DB4BC"})
    figs.append(style(f, CHART_TITLES[14], legend=True).update_xaxes(title="Price (R$, log)").update_yaxes(title="Freight (R$)"))

    return kpis + figs


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)),
            debug=os.environ.get("DASH_DEBUG", "0") == "1")
