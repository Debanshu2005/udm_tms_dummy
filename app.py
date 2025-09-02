from flask import Flask, request, render_template, Blueprint
import sqlite3, os, threading, webbrowser
from datetime import datetime, timedelta

app = Flask(__name__)
DB = "companion_data.db"

os.makedirs("templates", exist_ok=True)

# === Database setup ===
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS received (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE,
            item_type TEXT,
            vendor TEXT,
            lot TEXT,
            supply_date TEXT,
            warranty_end TEXT,
            manufactor_date TEXT,
            manufactor_number TEXT,
            repair_date TEXT,
            risk TEXT,
            vendor_risk TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === Helper functions ===
def compute_next_inspection(repair_date_str, risk_level):
    if not repair_date_str:
        return "Not scheduled"
    try:
        repair_dt = datetime.strptime(repair_date_str, "%Y-%m-%d")
    except ValueError:
        return "Invalid date"
    delta_days = {"High": 90, "Medium": 180, "Low": 365}.get(risk_level, 365)
    return (repair_dt + timedelta(days=delta_days)).strftime("%Y-%m-%d")

def fetch_all_rows():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM received ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# === /receive_data endpoint ===
@app.route('/receive_data', methods=['POST'])
def receive_data():
    data = request.json
    if not data:
        return {"status": "no data"}, 400

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO received (
            uid, item_type, vendor, lot, supply_date, warranty_end,
            manufactor_date, manufactor_number, repair_date,
            risk, vendor_risk, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(uid) DO UPDATE SET
            item_type=excluded.item_type,
            vendor=excluded.vendor,
            lot=excluded.lot,
            supply_date=excluded.supply_date,
            warranty_end=excluded.warranty_end,
            manufactor_date=excluded.manufactor_date,
            manufactor_number=excluded.manufactor_number,
            repair_date=excluded.repair_date,
            risk=excluded.risk,
            vendor_risk=excluded.vendor_risk,
            notes=excluded.notes
    """, (
        data.get("uid"), data.get("item_type"), data.get("vendor"), data.get("lot"),
        data.get("supply_date"), data.get("warranty_end"),
        data.get("manufactor_date"), data.get("manufactor_number"),
        data.get("repair_date"), data.get("risk"), data.get("vendor_risk"), data.get("notes")
    ))
    conn.commit()
    conn.close()
    return {"status": "success"}, 200

# === Blueprints ===

# UDM Blueprint (Dates)
udm_bp = Blueprint('udm', __name__, url_prefix="/udm", template_folder='templates')

@udm_bp.route('/')
def udm_home():
    rows = fetch_all_rows()
    for r in rows:
        r["next_inspection"] = compute_next_inspection(r.get("repair_date"), r.get("risk"))
    
    udm_rows = [
        {
            "uid": r["uid"],
            "item_type": r["item_type"],
            "supply_date": r["supply_date"],
            "warranty_end": r["warranty_end"],
            "repair_date": r["repair_date"],
            "next_inspection": r["next_inspection"]
        } for r in rows
    ]
    return render_template("udm.html", rows=udm_rows)

# TMS Blueprint (Risk Levels)
tms_bp = Blueprint('tms', __name__, url_prefix="/tms", template_folder='templates')

@tms_bp.route('/')
def tms_home():
    rows = fetch_all_rows()
    tms_rows = [
        {
            "uid": r["uid"],
            "item_type": r["item_type"],
            "risk": r["risk"],
            "vendor_risk": r["vendor_risk"]
        } for r in rows
    ]
    return render_template("tms.html", rows=tms_rows)

# Register Blueprints
app.register_blueprint(udm_bp)
app.register_blueprint(tms_bp)

# === Home route ===
@app.route('/')
def home():
    return """
    <h1>Unified Portal</h1>
    <p><a href='/udm'>Go to UDM (Dates)</a></p>
    <p><a href='/tms'>Go to TMS (Risk Levels)</a></p>
    """

# === Auto open browser ===
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5001/")

if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(debug=True, port=5001)
