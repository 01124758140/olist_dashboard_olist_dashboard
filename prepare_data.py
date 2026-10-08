"""
Shrinks the full olist_features.csv (57 columns) to only what the dashboard uses
and writes data/olist_features.csv.gz  (small enough for GitHub / free hosting).

Usage:
    python prepare_data.py "C:\\Users\\AFAQE\\Downloads\\archive (10)\\olist_features.csv"
"""
import sys
from pathlib import Path
import pandas as pd

USECOLS = [
    "order_id", "customer_unique_id", "customer_state", "order_status",
    "purchase_ts", "delivered_ts", "estimated_ts",
    "main_category", "payment_type", "installments",
    "n_items", "total_price", "total_freight", "order_value",
    "delivery_days", "delay_days", "is_late", "distance_km", "is_same_state",
    "review_score", "is_bad_review", "is_repeat_customer",
]

if len(sys.argv) != 2:
    sys.exit(__doc__)

src = Path(sys.argv[1])
out = Path(__file__).resolve().parent / "data" / "olist_features.csv.gz"
out.parent.mkdir(exist_ok=True)

df = pd.read_csv(src, usecols=USECOLS)
for c in ["total_price", "total_freight", "order_value", "delivery_days", "delay_days", "distance_km"]:
    df[c] = df[c].round(3)
df.to_csv(out, index=False, compression="gzip")
print(f"rows={len(df):,}  columns={df.shape[1]}  ->  {out}  ({out.stat().st_size/1e6:.1f} MB)")
