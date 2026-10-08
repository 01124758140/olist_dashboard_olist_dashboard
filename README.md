# Olist Marketplace Dashboard (Dash + Plotly)

15 KPI cards + 15 interactive charts + filters (date, state, category, payment, delivery status).

## Structure
```
app.py              # the dashboard (gunicorn entry point: app:server)
prepare_data.py     # shrinks olist_features.csv -> data/olist_features.csv.gz
data/               # put the data file here
requirements.txt
Procfile            # Railway / Heroku-style hosts
render.yaml         # Render
.python-version
```

## 1) Prepare the data (once)
```
python prepare_data.py "C:\Users\AFAQE\Downloads\archive (10)\olist_features.csv"
```
This creates `data/olist_features.csv.gz`. (You can also just copy `olist_features.csv` into `data/`.)

## 2) Run locally
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:8050

## 3) Deploy on Render
1. Push this folder to a GitHub repo (including `data/olist_features.csv.gz`).
2. Render -> New -> Web Service -> pick the repo. It reads `render.yaml` automatically.
   Or set manually: Build `pip install -r requirements.txt`, Start `gunicorn app:server --workers 1 --threads 4 --timeout 120`.
3. Wait for the build, then open the `.onrender.com` link.

Railway: same repo, it uses the `Procfile`.

Notes
- The geolocation file is NOT needed by the dashboard (only used in the notebook to compute distance_km). Don't upload it.
- Free Render instances sleep after inactivity; the first load can take ~1 minute.
- Custom data path: set env var `OLIST_DATA`.
