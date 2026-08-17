import sqlite3
from datetime import datetime, timedelta

DB = "companion_data.db"

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
