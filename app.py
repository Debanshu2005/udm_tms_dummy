from flask import Flask, request, render_template, Blueprint, redirect, url_for, jsonify, session
import sqlite3
import os
import json
import shutil
import tempfile
import secrets
from datetime import datetime, timedelta
from functools import wraps

try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "railqr-udm-tms-stable-key-2025")
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=86400,
)

# ── Environment ───────────────────────────────────────────────────────────────
IS_VERCEL = bool(os.environ.get("VERCEL"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_DIR = tempfile.gettempdir() if IS_VERCEL else BASE_DIR

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")
GAUGEMARKET_URL = os.environ.get("GAUGEMARKET_URL", "https://rail-qr-marketplace.vercel.app")
INTERNAL_SECRET = os.environ.get("GAUGEMARKET_INTERNAL_SECRET", "")
ALLOWED_ORIGINS_RAW = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://rail-qr-marketplace.vercel.app,http://localhost:5000,http://127.0.0.1:5000"
)
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS_RAW.split(",") if o.strip()]

# ── CORS setup ────────────────────────────────────────────────────────────────
if HAS_CORS:
    CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=False)

# ── Database path ─────────────────────────────────────────────────────────────
def _prepare_db():
    db_env = os.environ.get("UDM_DB_PATH")
    if db_env:
        return db_env
    source = os.path.join(BASE_DIR, "companion_data.db")
    if IS_VERCEL:
        target = os.path.join(RUNTIME_DIR, "companion_data.db")
        if os.path.exists(source) and not os.path.exists(target):
            shutil.copyfile(source, target)
        return target
    return source

DB = _prepare_db()

# ── Security headers ──────────────────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── Auth helpers ──────────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.path))
        return f(*args, **kwargs)
    return decorated

def require_internal_secret(f):
    """Guard for GaugeMarket → UDM/TMS server-to-server calls."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if INTERNAL_SECRET:
            provided = request.headers.get("X-Internal-Secret", "")
            if provided != INTERNAL_SECRET:
                return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ── Admin login ───────────────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            next_url = request.args.get("next") or url_for("home")
            return redirect(next_url)
        error = "Invalid password."
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Login — Indian Railways</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <style>
            :root {{
                --ir-blue: #1a3a6b;
                --ir-blue-dark: #0f2342;
                --ir-saffron: #f97316;
                --ir-light-gray: #f8f9fa;
            }}
            body {{
                font-family: 'Inter', sans-serif;
                background: linear-gradient(rgba(15, 35, 66, 0.9), rgba(15, 35, 66, 0.95)), url('/static/rail.jpg') center/cover no-repeat;
                min-height: 100vh;
                display: flex; flex-direction: column;
            }}
            .govt-bar {{
                background: #ffffff; border-bottom: 2px solid var(--ir-saffron);
                padding: 4px 0; font-size: 0.8rem; color: #475569; font-weight: 600;
                width: 100%; text-align: center;
            }}
            .login-wrapper {{
                flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px;
            }}
            .login-card {{
                background: #ffffff; border: none; border-radius: 16px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3); max-width: 420px; width: 100%;
                overflow: hidden; border-top: 4px solid var(--ir-saffron);
            }}
            .card-header-ir {{
                background: var(--ir-light-gray); padding: 30px 24px 24px; text-align: center;
                border-bottom: 1px solid #e2e8f0;
            }}
            .btn-ir {{
                background: var(--ir-saffron); color: white; border: none;
                border-radius: 8px; padding: 12px; font-weight: 700; font-size: 1rem;
                transition: all 0.3s;
            }}
            .btn-ir:hover {{ background: #ea580c; color: white; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(249,115,22,0.3); }}
            .form-control:focus {{
                border-color: var(--ir-blue); box-shadow: 0 0 0 3px rgba(26,58,107,0.15);
            }}
            .back-link {{ color: #cbd5e1; text-decoration: none; font-size: 0.9rem; font-weight: 600; transition: color 0.2s; }}
            .back-link:hover {{ color: #ffffff; text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="govt-bar">
            <span><i class="bi bi-bank"></i> भारत सरकार | GOVERNMENT OF INDIA &nbsp;&nbsp;|&nbsp;&nbsp; रेल मंत्रालय | MINISTRY OF RAILWAYS</span>
        </div>
        
        <div class="container mt-3">
            <a href="/" class="back-link"><i class="bi bi-arrow-left"></i> Back to Portal Home</a>
        </div>
        
        <div class="login-wrapper">
            <div class="login-card">
                <div class="card-header-ir">
                    <img src="/static/aazadi.jpg" alt="Azadi Logo" style="height:55px; margin-bottom:20px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                    <h4 class="fw-bold mb-1" style="color:var(--ir-blue-dark)">Authorized Access</h4>
                    <p style="color:#64748b; font-size:0.9rem; margin:0">RailQR Companion Portal (UDM/TMS)</p>
                </div>
                <div class="p-4">
                    {'<div class="alert alert-danger py-2" style="font-size:0.9rem; font-weight:600;"><i class="bi bi-exclamation-triangle-fill me-2"></i>'+error+'</div>' if error else ''}
                    <form method="POST">
                        <div class="mb-4">
                            <label class="form-label fw-semibold" style="color:#475569; font-size:0.9rem">Administrator Password</label>
                            <input type="password" name="password" class="form-control form-control-lg" style="font-size:1rem;" placeholder="Enter secure password" autofocus required>
                        </div>
                        <button type="submit" class="btn-ir w-100">
                            <i class="bi bi-shield-lock-fill me-2"></i> Sign In to Dashboard
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("home"))

# ── Database setup ────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Core component registry — synced from GaugeMarket
    c.execute("""
        CREATE TABLE IF NOT EXISTS received (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE NOT NULL,
            item_type TEXT,
            vendor TEXT,
            vendor_id TEXT,
            lot TEXT,
            supply_date TEXT,
            warranty_end TEXT,
            manufactor_date TEXT,
            manufactor_number TEXT,
            repair_date TEXT,
            risk TEXT DEFAULT 'Low',
            vendor_risk TEXT DEFAULT 'Low',
            notes TEXT,
            lifecycle_status TEXT DEFAULT 'REGISTERED',
            synced_at TEXT
        )
    """)

    # Ensure lifecycle_status column exists (migration safety)
    c.execute("PRAGMA table_info(received)")
    existing = {row[1] for row in c.fetchall()}
    for col, coltype in [
        ("vendor_id", "TEXT"),
        ("lifecycle_status", "TEXT DEFAULT 'REGISTERED'"),
        ("synced_at", "TEXT"),
    ]:
        if col not in existing:
            c.execute(f"ALTER TABLE received ADD COLUMN {col} {coltype}")

    # Technician inspection log (original TMS — tracking component health)
    c.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            inspection_date TEXT NOT NULL,
            condition TEXT,
            severity TEXT DEFAULT 'Low',
            technician TEXT,
            observations TEXT,
            actions_taken TEXT,
            photos TEXT,
            location_data TEXT,
            FOREIGN KEY (uid) REFERENCES received (uid)
        )
    """)

    # Vendors mirror
    c.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            email TEXT,
            contact TEXT,
            risk_level TEXT DEFAULT 'Low',
            failure_count INTEGER DEFAULT 0
        )
    """)

    # ── TMS Transport layer ───────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS tms_shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gaugemarket_order_id INTEGER,
            order_no TEXT NOT NULL,
            vendor_id TEXT,
            vendor_name TEXT,
            courier TEXT DEFAULT 'Indian Railways Logistics',
            tracking_number TEXT UNIQUE,
            origin TEXT,
            destination TEXT,
            status TEXT DEFAULT 'SHIPMENT_CREATED',
            eta TEXT,
            gaugemarket_synced INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            dispatched_at TEXT,
            delivered_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tms_shipment_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER NOT NULL,
            tracking_number TEXT,
            event_type TEXT NOT NULL,
            location TEXT,
            description TEXT,
            actor TEXT,
            event_time TEXT NOT NULL,
            FOREIGN KEY (shipment_id) REFERENCES tms_shipments(id)
        )
    """)

    # Component lifecycle event log (UDM traceability)
    c.execute("""
        CREATE TABLE IF NOT EXISTS lifecycle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT,
            actor TEXT,
            source TEXT DEFAULT 'UDM',
            event_time TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ── Helper functions ──────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def compute_next_inspection(repair_date_str, risk_level):
    if not repair_date_str:
        return "Not scheduled"
    try:
        repair_dt = datetime.strptime(repair_date_str, "%Y-%m-%d")
    except ValueError:
        return "Invalid date"
    delta_days = {"High": 90, "Medium": 180, "Low": 365}.get(risk_level, 365)
    return (repair_dt + timedelta(days=delta_days)).strftime("%Y-%m-%d")

def is_date_soon(date_string, days=30):
    try:
        if not date_string or date_string in ("None", "Not scheduled", "Invalid date"):
            return False
        target = datetime.strptime(date_string, "%Y-%m-%d")
        today = datetime.now()
        return today <= target <= today + timedelta(days=days)
    except Exception:
        return False

def warranty_status(warranty_end_str):
    if not warranty_end_str:
        return "UNKNOWN"
    try:
        end = datetime.strptime(warranty_end_str, "%Y-%m-%d").date()
        today = datetime.today().date()
        if end < today:
            return "EXPIRED"
        if (end - today).days <= 90:
            return "EXPIRING_SOON"
        return "ACTIVE"
    except Exception:
        return "UNKNOWN"

def fetch_all_rows():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM received ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_record_by_uid(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM received WHERE uid=?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def generate_tracking_number():
    """Generate a unique IRLs-style tracking number."""
    prefix = "IRL"
    timestamp = datetime.now().strftime("%y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"{prefix}{timestamp}{random_part}"

def record_lifecycle_event(uid, event_type, description, actor="SYSTEM", source="UDM"):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO lifecycle_events (uid, event_type, description, actor, source, event_time) VALUES (?,?,?,?,?,?)",
            (uid, event_type, description, actor, source, now_iso())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[LifecycleEvent] {e}")

def notify_gaugemarket(path, payload, method="POST"):
    """Fire-and-forget notification back to GaugeMarket. Non-blocking best-effort."""
    try:
        import requests as req
        url = f"{GAUGEMARKET_URL.rstrip('/')}{path}"
        headers = {"Content-Type": "application/json"}
        if INTERNAL_SECRET:
            headers["X-Internal-Secret"] = INTERNAL_SECRET
        if method.upper() == "POST":
            req.post(url, json=payload, headers=headers, timeout=5)
        else:
            req.get(url, params=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"[GaugeMarket callback] {e}")

# ── /receive_data — called by GaugeMarket push_to_udm / push_to_tms ──────────
@app.route("/receive_data", methods=["POST"])
def receive_data():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400
    uid = data.get("uid")
    if not uid:
        return jsonify({"status": "error", "message": "Missing uid"}), 400

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    lifecycle = data.get("lifecycle_status", "REGISTERED")
    c.execute("""
        INSERT INTO received (
            uid, item_type, vendor, vendor_id, lot, supply_date, warranty_end,
            manufactor_date, manufactor_number, repair_date,
            risk, vendor_risk, notes, lifecycle_status, synced_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(uid) DO UPDATE SET
            item_type=excluded.item_type,
            vendor=excluded.vendor,
            vendor_id=excluded.vendor_id,
            lot=excluded.lot,
            supply_date=excluded.supply_date,
            warranty_end=excluded.warranty_end,
            manufactor_date=excluded.manufactor_date,
            manufactor_number=excluded.manufactor_number,
            repair_date=excluded.repair_date,
            risk=excluded.risk,
            vendor_risk=excluded.vendor_risk,
            notes=excluded.notes,
            lifecycle_status=excluded.lifecycle_status,
            synced_at=excluded.synced_at
    """, (
        uid, data.get("item_type"), data.get("vendor"), data.get("vendor_id"),
        data.get("lot"), data.get("supply_date"), data.get("warranty_end"),
        data.get("manufactor_date"), data.get("manufactor_number"),
        data.get("repair_date"), data.get("risk"), data.get("vendor_risk"),
        data.get("notes"), lifecycle, now_iso()
    ))
    conn.commit()
    conn.close()

    # Record lifecycle event for REGISTERED components arriving for the first time
    record_lifecycle_event(uid, "SYNCED_FROM_GAUGEMARKET",
                           f"Component data synced. Lifecycle: {lifecycle}",
                           actor=data.get("vendor", "VENDOR"), source="GAUGEMARKET")
    return jsonify({"status": "success"}), 200

# ── View routes ───────────────────────────────────────────────────────────────
@app.route("/view/<uid>")
def view_record(uid):
    record = get_record_by_uid(uid)
    if not record:
        return "Fitting not found", 404
    record["next_inspection"] = compute_next_inspection(record.get("repair_date"), record.get("risk"))
    record["warranty_status"] = warranty_status(record.get("warranty_end"))
    conn = get_conn()
    events = conn.execute(
        "SELECT * FROM lifecycle_events WHERE uid=? ORDER BY event_time ASC", (uid,)
    ).fetchall()
    insp = conn.execute(
        "SELECT * FROM inspections WHERE uid=? ORDER BY inspection_date DESC", (uid,)
    ).fetchall()
    conn.close()
    return render_template("view.html", row=record,
                           events=[dict(e) for e in events],
                           inspections=[dict(i) for i in insp])

@app.route("/all")
@admin_required
def view_all():
    rows = fetch_all_rows()
    for r in rows:
        r["next_inspection"] = compute_next_inspection(r.get("repair_date"), r.get("risk"))
        r["warranty_status"] = warranty_status(r.get("warranty_end"))
    return render_template("all.html", rows=rows)

# ── UDM Blueprint ─────────────────────────────────────────────────────────────
udm_bp = Blueprint("udm", __name__, url_prefix="/udm", template_folder="../templates")

@udm_bp.route("/")
@admin_required
def udm_home():
    rows = fetch_all_rows()
    for r in rows:
        r["next_inspection"] = compute_next_inspection(r.get("repair_date"), r.get("risk"))
        r["warranty_status"] = warranty_status(r.get("warranty_end"))

    conn = get_conn()
    vendors = [row["vendor"] for row in conn.execute(
        "SELECT DISTINCT vendor FROM received WHERE vendor IS NOT NULL"
    ).fetchall()]

    # Real analytics for charts
    total = len(rows)
    warranty_counts = {"ACTIVE": 0, "EXPIRING_SOON": 0, "EXPIRED": 0, "UNKNOWN": 0}
    risk_counts = {"High": 0, "Medium": 0, "Low": 0}
    lifecycle_counts = {}
    vendor_risk_map = {}

    for r in rows:
        ws = r.get("warranty_status", "UNKNOWN")
        warranty_counts[ws] = warranty_counts.get(ws, 0) + 1
        rl = r.get("risk", "Low")
        risk_counts[rl] = risk_counts.get(rl, 0) + 1
        ls = r.get("lifecycle_status", "REGISTERED")
        lifecycle_counts[ls] = lifecycle_counts.get(ls, 0) + 1
        v = r.get("vendor")
        if v:
            vr = r.get("vendor_risk", "Low")
            if v not in vendor_risk_map:
                vendor_risk_map[v] = {"vendor": v, "count": 0, "high": 0}
            vendor_risk_map[v]["count"] += 1
            if vr == "High":
                vendor_risk_map[v]["high"] += 1

    # Upcoming inspections (within 30 days)
    upcoming_inspections = [r for r in rows if is_date_soon(r.get("next_inspection"))]
    expiring_warranty = [r for r in rows if r.get("warranty_status") == "EXPIRING_SOON"]
    high_risk_vendors = [v for v, d in vendor_risk_map.items() if d["high"] > 0]

    # Recent lifecycle events
    recent_events = conn.execute(
        "SELECT * FROM lifecycle_events ORDER BY event_time DESC LIMIT 20"
    ).fetchall()
    conn.close()

    return render_template(
        "udm.html",
        rows=rows,
        vendors=vendors,
        is_date_soon=is_date_soon,
        warranty_counts=warranty_counts,
        risk_counts=risk_counts,
        lifecycle_counts=lifecycle_counts,
        vendor_risk_map=list(vendor_risk_map.values()),
        upcoming_inspections=upcoming_inspections,
        expiring_warranty=expiring_warranty,
        high_risk_vendors=high_risk_vendors,
        recent_events=[dict(e) for e in recent_events],
        gaugemarket_url=GAUGEMARKET_URL,
    )

# UDM JSON APIs
@udm_bp.route("/api/fittings", methods=["GET"])
def api_get_fittings():
    conn = get_conn()
    rows = conn.execute(
        "SELECT uid, vendor, supply_date, warranty_end, repair_date, risk, lifecycle_status FROM received"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@udm_bp.route("/api/fitting/<uid>", methods=["GET"])
def api_get_fitting(uid):
    conn = get_conn()
    row = conn.execute(
        "SELECT uid, vendor, supply_date, warranty_end, repair_date, risk, lifecycle_status FROM received WHERE uid=?",
        (uid,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Fitting not found"}), 404
    return jsonify(dict(row))

@udm_bp.route("/api/fitting/<uid>", methods=["POST"])
def api_update_fitting_dates(uid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    conn = get_conn()
    conn.execute(
        "UPDATE received SET supply_date=?, warranty_end=?, repair_date=? WHERE uid=?",
        (data.get("supply_date"), data.get("warranty_end"), data.get("repair_date"), uid)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Fitting dates updated"})

# ── TMS Blueprint ─────────────────────────────────────────────────────────────
tms_bp = Blueprint("tms", __name__, url_prefix="/tms", template_folder="../templates")

@tms_bp.route("/")
@admin_required
def tms_home():
    rows = fetch_all_rows()
    risk_stats = {
        "High": len([r for r in rows if r.get("risk") == "High"]),
        "Medium": len([r for r in rows if r.get("risk") == "Medium"]),
        "Low": len([r for r in rows if r.get("risk") == "Low"]),
    }
    high_risk_vendors = list(set(
        r.get("vendor") for r in rows if r.get("vendor_risk") == "High" and r.get("vendor")
    ))
    conn = get_conn()
    shipments = conn.execute(
        "SELECT * FROM tms_shipments ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    shipment_stats = {
        "total": conn.execute("SELECT COUNT(*) FROM tms_shipments").fetchone()[0],
        "in_transit": conn.execute(
            "SELECT COUNT(*) FROM tms_shipments WHERE status IN ('IN_TRANSIT','PICKED_UP','ARRIVED_AT_HUB','OUT_FOR_DELIVERY')"
        ).fetchone()[0],
        "delivered": conn.execute(
            "SELECT COUNT(*) FROM tms_shipments WHERE status='DELIVERED'"
        ).fetchone()[0],
        "pending": conn.execute(
            "SELECT COUNT(*) FROM tms_shipments WHERE status IN ('SHIPMENT_CREATED','PICKUP_PENDING')"
        ).fetchone()[0],
    }
    conn.close()
    return render_template(
        "tms.html",
        rows=rows,
        risk_stats=risk_stats,
        high_risk_vendors=high_risk_vendors,
        shipments=[dict(s) for s in shipments],
        shipment_stats=shipment_stats,
        gaugemarket_url=GAUGEMARKET_URL,
    )

# TMS component risk APIs
@tms_bp.route("/api/risks", methods=["GET"])
def api_get_risks():
    conn = get_conn()
    rows = conn.execute("SELECT uid, vendor, risk, vendor_risk FROM received").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@tms_bp.route("/api/fitting/<uid>/risk", methods=["POST"])
def api_update_risk(uid):
    data = request.get_json()
    if not data or "risk" not in data:
        return jsonify({"error": "Missing risk field"}), 400
    new_risk = data["risk"]
    if new_risk not in ("Low", "Medium", "High", "CRITICAL"):
        return jsonify({"error": "Invalid risk level"}), 400
    conn = get_conn()
    conn.execute("UPDATE received SET risk=? WHERE uid=?", (new_risk, uid))
    conn.commit()
    conn.close()
    record_lifecycle_event(uid, "RISK_UPDATED", f"Risk level updated to {new_risk}",
                           actor=data.get("technician", "SYSTEM"), source="TMS")
    return jsonify({"status": "success", "message": f"Risk updated to {new_risk}"})

@tms_bp.route("/api/fitting/<uid>/inspections", methods=["GET"])
def api_get_fitting_inspections(uid):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM inspections WHERE uid=? ORDER BY inspection_date DESC", (uid,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@tms_bp.route("/api/fitting/<uid>/inspection", methods=["POST"])
def api_add_inspection(uid):
    data = request.get_json()
    if not data or "condition" not in data or "severity" not in data:
        return jsonify({"error": "Missing condition or severity"}), 400
    conn = get_conn()
    conn.execute("""
        INSERT INTO inspections (uid, inspection_date, condition, severity, technician,
                                 observations, actions_taken, photos, location_data)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        uid, now_iso(),
        data.get("condition"), data.get("severity"),
        data.get("technician", "unknown"),
        data.get("observations", ""), data.get("actions_taken", ""),
        json.dumps(data.get("photos", [])), json.dumps(data.get("location", {}))
    ))
    conn.commit()
    conn.close()
    record_lifecycle_event(uid, "INSPECTION_RECORDED",
                           f"Condition: {data.get('condition')}. Severity: {data.get('severity')}",
                           actor=data.get("technician", "SYSTEM"), source="TMS")
    return jsonify({"status": "success", "message": "Inspection added"})

# Register blueprints
app.register_blueprint(udm_bp)
app.register_blueprint(tms_bp)

# ── Global UDM API (canonical paths) ─────────────────────────────────────────
@app.route("/api/udm/fittings/<uid>", methods=["GET"])
def get_fitting_api(uid):
    record = get_record_by_uid(uid)
    if not record:
        return jsonify({"error": "Fitting not found"}), 404
    record["next_inspection"] = compute_next_inspection(record.get("repair_date"), record.get("risk"))
    record["warranty_status"] = warranty_status(record.get("warranty_end"))
    return jsonify(record)

@app.route("/api/udm/fittings/search", methods=["GET"])
def search_fittings_api():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Search term required"}), 400
    conn = get_conn()
    rows = conn.execute("""
        SELECT uid, item_type, vendor, risk, lifecycle_status
        FROM received
        WHERE uid LIKE ? OR item_type LIKE ? OR vendor LIKE ?
        ORDER BY risk DESC, uid ASC LIMIT 20
    """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/udm/fittings/<uid>/update", methods=["POST"])
def update_fitting_api(uid):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    conn = get_conn()
    if not conn.execute("SELECT id FROM received WHERE uid=?", (uid,)).fetchone():
        conn.close()
        return jsonify({"error": "Fitting not found"}), 404
    fields, values = [], []
    for field in ("notes", "risk", "repair_date"):
        if field in data:
            fields.append(f"{field}=?")
            values.append(data[field])
    if not fields:
        conn.close()
        return jsonify({"error": "No valid fields to update"}), 400
    values.append(uid)
    conn.execute(f"UPDATE received SET {', '.join(fields)} WHERE uid=?", values)
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Fitting updated"})

# ── UDM Component API (canonical — maps components to GaugeMarket UIDs) ──────
@app.route("/api/udm/components/<uid>", methods=["GET"])
def get_component(uid):
    record = get_record_by_uid(uid)
    if not record:
        return jsonify({"error": "Component not found"}), 404
    record["next_inspection"] = compute_next_inspection(record.get("repair_date"), record.get("risk"))
    record["warranty_status"] = warranty_status(record.get("warranty_end"))
    conn = get_conn()
    # Latest shipment for this component's order
    shipment = conn.execute("""
        SELECT s.* FROM tms_shipments s
        JOIN received r ON r.uid=?
        WHERE s.order_no IS NOT NULL
        ORDER BY s.created_at DESC LIMIT 1
    """, (uid,)).fetchone()
    conn.close()
    result = {**record}
    if shipment:
        result["latest_shipment"] = dict(shipment)
    return jsonify(result)

@app.route("/api/udm/components/<uid>/history", methods=["GET"])
def get_component_history(uid):
    conn = get_conn()
    events = conn.execute(
        "SELECT * FROM lifecycle_events WHERE uid=? ORDER BY event_time ASC", (uid,)
    ).fetchall()
    inspections = conn.execute(
        "SELECT * FROM inspections WHERE uid=? ORDER BY inspection_date DESC", (uid,)
    ).fetchall()
    conn.close()
    return jsonify({
        "uid": uid,
        "lifecycle_events": [dict(e) for e in events],
        "inspections": [dict(i) for i in inspections],
    })

@app.route("/api/udm/components/<uid>/inspections", methods=["GET"])
def get_component_inspections(uid):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM inspections WHERE uid=? ORDER BY inspection_date DESC", (uid,)
    ).fetchall()
    conn.close()
    return jsonify({"uid": uid, "inspections": [dict(r) for r in rows]})

@app.route("/api/udm/components/<uid>/lifecycle", methods=["POST"])
def update_component_lifecycle(uid):
    data = request.json or {}
    new_status = data.get("lifecycle_status")
    valid_statuses = {
        "REGISTERED", "VERIFIED", "INSPECTED", "LISTED",
        "PURCHASED", "PACKED", "SHIPPED", "IN_TRANSIT",
        "DELIVERED", "ASSIGNED", "INSTALLED", "MAINTENANCE",
        "REINSPECTION", "RETIRED"
    }
    if not new_status or new_status not in valid_statuses:
        return jsonify({"error": f"Invalid lifecycle_status. Valid: {sorted(valid_statuses)}"}), 400
    conn = get_conn()
    if not conn.execute("SELECT id FROM received WHERE uid=?", (uid,)).fetchone():
        conn.close()
        return jsonify({"error": "Component not found"}), 404
    conn.execute("UPDATE received SET lifecycle_status=?, synced_at=? WHERE uid=?",
                 (new_status, now_iso(), uid))
    conn.commit()
    conn.close()
    record_lifecycle_event(uid, "LIFECYCLE_UPDATED",
                           f"Lifecycle status changed to {new_status}",
                           actor=data.get("actor", "SYSTEM"),
                           source=data.get("source", "UDM"))
    return jsonify({"status": "success", "uid": uid, "lifecycle_status": new_status})

# ── TMS Shipment API (canonical) ──────────────────────────────────────────────
@app.route("/api/tms/shipments", methods=["POST"])
@require_internal_secret
def create_shipment():
    """Called by GaugeMarket when a vendor marks an order as shipped."""
    data = request.json or {}
    required = ["order_no"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    tracking_number = data.get("tracking_number") or generate_tracking_number()
    created_at = now_iso()

    conn = get_conn()
    try:
        cursor = conn.execute("""
            INSERT INTO tms_shipments (
                gaugemarket_order_id, order_no, vendor_id, vendor_name,
                courier, tracking_number, origin, destination,
                status, eta, created_at, dispatched_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("gaugemarket_order_id"),
            data["order_no"],
            data.get("vendor_id"),
            data.get("vendor_name"),
            data.get("courier", "Indian Railways Logistics"),
            tracking_number,
            data.get("origin"),
            data.get("destination"),
            "SHIPMENT_CREATED",
            data.get("eta"),
            created_at,
            data.get("dispatched_at"),
        ))
        shipment_id = cursor.lastrowid
        # First event
        conn.execute("""
            INSERT INTO tms_shipment_events (shipment_id, tracking_number, event_type,
                                             location, description, actor, event_time)
            VALUES (?,?,?,?,?,?,?)
        """, (shipment_id, tracking_number, "SHIPMENT_CREATED",
              data.get("origin", "Vendor Warehouse"),
              "Shipment record created. Awaiting pickup.",
              data.get("vendor_name", "VENDOR"), created_at))
        conn.commit()

        # Update component lifecycle for each UID in the order
        order_no = data["order_no"]
        uids = data.get("uids", [])
        for uid in uids:
            conn.execute(
                "UPDATE received SET lifecycle_status='SHIPPED', synced_at=? WHERE uid=?",
                (created_at, uid)
            )
            record_lifecycle_event(uid, "SHIPMENT_CREATED",
                                   f"Shipment {tracking_number} created for order {order_no}",
                                   actor=data.get("vendor_name", "VENDOR"), source="TMS")
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Tracking number already exists"}), 409
    conn.close()
    return jsonify({
        "status": "success",
        "shipment_id": shipment_id,
        "tracking_number": tracking_number,
    }), 201

@app.route("/api/tms/shipments/<int:shipment_id>", methods=["GET"])
def get_shipment(shipment_id):
    conn = get_conn()
    shipment = conn.execute(
        "SELECT * FROM tms_shipments WHERE id=?", (shipment_id,)
    ).fetchone()
    if not shipment:
        conn.close()
        return jsonify({"error": "Shipment not found"}), 404
    events = conn.execute(
        "SELECT * FROM tms_shipment_events WHERE shipment_id=? ORDER BY event_time ASC",
        (shipment_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        "shipment": dict(shipment),
        "events": [dict(e) for e in events],
    })

@app.route("/api/tms/shipments/<int:shipment_id>/events", methods=["POST"])
def add_shipment_event(shipment_id):
    data = request.json or {}
    if not data.get("event_type"):
        return jsonify({"error": "Missing event_type"}), 400

    valid_events = {
        "SHIPMENT_CREATED", "PICKUP_PENDING", "PICKED_UP", "IN_TRANSIT",
        "ARRIVED_AT_HUB", "OUT_FOR_DELIVERY", "DELIVERED", "EXCEPTION",
        "RETURNED", "CUSTOM_EVENT"
    }
    event_type = data["event_type"]
    if event_type not in valid_events:
        event_type = "CUSTOM_EVENT"

    conn = get_conn()
    shipment = conn.execute(
        "SELECT * FROM tms_shipments WHERE id=?", (shipment_id,)
    ).fetchone()
    if not shipment:
        conn.close()
        return jsonify({"error": "Shipment not found"}), 404

    shipment = dict(shipment)
    event_time = now_iso()
    conn.execute("""
        INSERT INTO tms_shipment_events (shipment_id, tracking_number, event_type,
                                         location, description, actor, event_time)
        VALUES (?,?,?,?,?,?,?)
    """, (
        shipment_id, shipment["tracking_number"],
        event_type, data.get("location"), data.get("description"),
        data.get("actor", "SYSTEM"), event_time
    ))

    # Update shipment status
    status_map = {
        "PICKED_UP": "PICKED_UP",
        "IN_TRANSIT": "IN_TRANSIT",
        "ARRIVED_AT_HUB": "ARRIVED_AT_HUB",
        "OUT_FOR_DELIVERY": "OUT_FOR_DELIVERY",
        "DELIVERED": "DELIVERED",
        "PICKUP_PENDING": "PICKUP_PENDING",
    }
    new_status = status_map.get(event_type, shipment["status"])
    update_sql = "UPDATE tms_shipments SET status=?"
    update_vals = [new_status]
    if event_type == "PICKED_UP" and not shipment.get("dispatched_at"):
        update_sql += ", dispatched_at=?"
        update_vals.append(event_time)
    if event_type == "DELIVERED":
        update_sql += ", delivered_at=?"
        update_vals.append(event_time)
    update_vals.append(shipment_id)
    conn.execute(update_sql + " WHERE id=?", update_vals)
    conn.commit()
    conn.close()

    # If delivered, callback to GaugeMarket and update UDM
    if event_type == "DELIVERED":
        _handle_delivery(shipment, event_time)

    return jsonify({"status": "success", "event_type": event_type, "shipment_status": new_status}), 201

@app.route("/api/tms/shipments/<int:shipment_id>/events", methods=["GET"])
def get_shipment_events(shipment_id):
    conn = get_conn()
    events = conn.execute(
        "SELECT * FROM tms_shipment_events WHERE shipment_id=? ORDER BY event_time ASC",
        (shipment_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(e) for e in events])

@app.route("/api/tms/tracking/<tracking_number>", methods=["GET"])
def track_by_number(tracking_number):
    """Public tracking endpoint — returns only safe public information."""
    conn = get_conn()
    shipment = conn.execute(
        "SELECT id, order_no, courier, tracking_number, status, eta, created_at, delivered_at "
        "FROM tms_shipments WHERE tracking_number=?", (tracking_number,)
    ).fetchone()
    if not shipment:
        conn.close()
        return jsonify({"error": "Tracking number not found"}), 404
    shipment = dict(shipment)
    events = conn.execute(
        "SELECT event_type, location, description, event_time FROM tms_shipment_events "
        "WHERE shipment_id=? ORDER BY event_time ASC", (shipment["id"],)
    ).fetchall()
    conn.close()
    return jsonify({
        "tracking_number": tracking_number,
        "status": shipment["status"],
        "courier": shipment["courier"],
        "eta": shipment["eta"],
        "created_at": shipment["created_at"],
        "delivered_at": shipment.get("delivered_at"),
        "events": [dict(e) for e in events],
    })

def _handle_delivery(shipment, delivered_at):
    """Update GaugeMarket + UDM when a shipment is delivered."""
    order_no = shipment.get("order_no")
    # Notify GaugeMarket
    notify_gaugemarket("/api/internal/order-delivered", {
        "order_no": order_no,
        "tracking_number": shipment.get("tracking_number"),
        "delivered_at": delivered_at,
    })
    # Update any components associated with this order in UDM
    conn = get_conn()
    # Find UIDs from lifecycle events that reference this order
    events = conn.execute(
        "SELECT DISTINCT uid FROM lifecycle_events WHERE description LIKE ?",
        (f"%{order_no}%",)
    ).fetchall()
    for row in events:
        uid = row["uid"]
        conn.execute(
            "UPDATE received SET lifecycle_status='DELIVERED', synced_at=? WHERE uid=?",
            (delivered_at, uid)
        )
        record_lifecycle_event(uid, "DELIVERED",
                               f"Shipment {shipment.get('tracking_number')} delivered for order {order_no}",
                               actor="TMS", source="TMS")
    conn.commit()
    conn.close()

# ── Internal callback endpoint (called by GaugeMarket or TMS) ─────────────────
@app.route("/api/internal/mark-delivered", methods=["POST"])
@require_internal_secret
def mark_delivered():
    """GaugeMarket can call this to confirm delivery. TMS also calls itself via _handle_delivery."""
    data = request.json or {}
    shipment_id = data.get("shipment_id")
    tracking_number = data.get("tracking_number")

    conn = get_conn()
    if shipment_id:
        shipment = conn.execute("SELECT * FROM tms_shipments WHERE id=?", (shipment_id,)).fetchone()
    elif tracking_number:
        shipment = conn.execute("SELECT * FROM tms_shipments WHERE tracking_number=?", (tracking_number,)).fetchone()
    else:
        conn.close()
        return jsonify({"error": "Provide shipment_id or tracking_number"}), 400

    if not shipment:
        conn.close()
        return jsonify({"error": "Shipment not found"}), 404

    shipment = dict(shipment)
    delivered_at = data.get("delivered_at", now_iso())
    conn.execute(
        "UPDATE tms_shipments SET status='DELIVERED', delivered_at=?, gaugemarket_synced=1 WHERE id=?",
        (delivered_at, shipment["id"])
    )
    conn.execute("""
        INSERT INTO tms_shipment_events (shipment_id, tracking_number, event_type,
                                         location, description, actor, event_time)
        VALUES (?,?,?,?,?,?,?)
    """, (shipment["id"], shipment["tracking_number"], "DELIVERED",
          data.get("location"), "Marked delivered via internal API.",
          "SYSTEM", delivered_at))
    conn.commit()
    conn.close()
    _handle_delivery(shipment, delivered_at)
    return jsonify({"status": "success", "tracking_number": shipment["tracking_number"]})

# ── TMS Inspections (legacy global endpoints — kept for GaugeMarket compat) ───
@app.route("/api/tms/inspections", methods=["POST"])
def add_inspection():
    data = request.json or {}
    uid = data.get("uid")
    if not uid:
        return jsonify({"error": "Missing UID"}), 400
    conn = get_conn()
    if not conn.execute("SELECT id FROM received WHERE uid=?", (uid,)).fetchone():
        conn.close()
        return jsonify({"error": "Fitting not found"}), 404
    inspection_date = now_iso()
    conn.execute("""
        INSERT INTO inspections (uid, inspection_date, condition, severity, technician,
                                 observations, actions_taken, photos, location_data)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        uid, inspection_date,
        data.get("condition", ""), data.get("severity", "Low"),
        data.get("technician_id", "unknown"),
        data.get("observations", ""), data.get("actions_taken", ""),
        json.dumps(data.get("photos", [])), json.dumps(data.get("location", {}))
    ))
    # Update risk if severity escalates
    current = conn.execute("SELECT risk FROM received WHERE uid=?", (uid,)).fetchone()
    if current:
        risk_map = {"Low": 0, "Medium": 1, "High": 2}
        new_sev = data.get("severity", "Low")
        cur_risk = current["risk"] or "Low"
        if risk_map.get(new_sev, 0) > risk_map.get(cur_risk, 0):
            conn.execute("UPDATE received SET risk=?, repair_date=? WHERE uid=?",
                         (new_sev, datetime.now().strftime("%Y-%m-%d"), uid))
    conn.commit()
    final_risk = conn.execute("SELECT risk FROM received WHERE uid=?", (uid,)).fetchone()["risk"]
    conn.close()
    record_lifecycle_event(uid, "INSPECTION_COMPLETED",
                           f"Inspection completed. Severity: {data.get('severity', 'Low')}",
                           actor=data.get("technician_id", "SYSTEM"), source="TMS")
    return jsonify({
        "status": "success",
        "new_risk_level": final_risk,
        "next_inspection": compute_next_inspection(datetime.now().strftime("%Y-%m-%d"), final_risk)
    })

@app.route("/api/tms/inspections/<uid>", methods=["GET"])
def get_inspections(uid):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM inspections WHERE uid=? ORDER BY inspection_date DESC", (uid,)
    ).fetchall()
    conn.close()
    return jsonify({"uid": uid, "inspections": [dict(r) for r in rows], "total": len(rows)})

@app.route("/api/tms/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM received").fetchone()[0]
    risk_rows = conn.execute("SELECT risk, COUNT(*) as c FROM received GROUP BY risk").fetchall()
    risk_stats = {r["risk"]: r["c"] for r in risk_rows}
    recent_insp = conn.execute(
        "SELECT COUNT(*) FROM inspections WHERE inspection_date >= date('now', '-7 days')"
    ).fetchone()[0]
    ship_stats = {
        "total": conn.execute("SELECT COUNT(*) FROM tms_shipments").fetchone()[0],
        "in_transit": conn.execute(
            "SELECT COUNT(*) FROM tms_shipments WHERE status IN ('IN_TRANSIT','PICKED_UP','ARRIVED_AT_HUB','OUT_FOR_DELIVERY')"
        ).fetchone()[0],
        "delivered": conn.execute("SELECT COUNT(*) FROM tms_shipments WHERE status='DELIVERED'").fetchone()[0],
    }
    conn.close()
    return jsonify({
        "total_components": total,
        "risk_stats": risk_stats,
        "recent_inspections_7d": recent_insp,
        "shipment_stats": ship_stats,
    })

@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        conn = get_conn()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "vercel": IS_VERCEL,
            "gaugemarket_url": GAUGEMARKET_URL,
        })
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# ── Home ──────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    conn = get_conn()
    total_components = conn.execute("SELECT COUNT(*) FROM received").fetchone()[0]
    total_shipments = conn.execute("SELECT COUNT(*) FROM tms_shipments").fetchone()[0]
    high_risk = conn.execute("SELECT COUNT(*) FROM received WHERE risk='High'").fetchone()[0]
    in_transit = conn.execute(
        "SELECT COUNT(*) FROM tms_shipments WHERE status IN ('IN_TRANSIT','PICKED_UP','ARRIVED_AT_HUB','OUT_FOR_DELIVERY')"
    ).fetchone()[0]
    conn.close()
    is_admin = session.get("admin_logged_in", False)
    return render_template("index.html",
                           total_components=total_components,
                           total_shipments=total_shipments,
                           high_risk=high_risk,
                           in_transit=in_transit,
                           is_admin=is_admin,
                           gaugemarket_url=GAUGEMARKET_URL)
