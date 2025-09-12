from flask import Flask, request, render_template, Blueprint, redirect, url_for, jsonify
import sqlite3, os, threading, webbrowser
from datetime import datetime, timedelta

app = Flask(__name__)
DB = "companion_data.db"

os.makedirs("templates", exist_ok=True)

# === Database setup ===
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Main fittings table
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
    
    # Inspections table
    c.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT,
            inspection_date TEXT,
            condition TEXT,
            severity TEXT,
            technician TEXT,
            observations TEXT,
            actions_taken TEXT,
            photos TEXT,
            location_data TEXT,
            FOREIGN KEY (uid) REFERENCES received (uid)
        )
    """)
    
    # Vendors table (if it doesn't exist)
    c.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            email TEXT,
            contact TEXT,
            risk_level TEXT DEFAULT 'Low',
            failure_count INTEGER DEFAULT 0
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

def is_date_soon(date_string):
    """Check if a date is within the next 30 days"""
    try:
        if not date_string or date_string == 'None':
            return False
        target_date = datetime.strptime(date_string, "%Y-%m-%d")
        today = datetime.now()
        return today <= target_date <= today + timedelta(days=30)
    except:
        return False

def fetch_all_rows():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM received ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_record_by_uid(uid):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM received WHERE uid=?", (uid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

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

# === View record endpoint ===
@app.route('/view/<uid>')
def view_record(uid):
    record = get_record_by_uid(uid)
    if not record:
        return "Fitting not found", 404
    record["next_inspection"] = compute_next_inspection(record.get("repair_date"), record.get("risk"))
    return render_template('view.html', row=record)

# === All records endpoint ===
@app.route('/all')
def view_all():
    rows = fetch_all_rows()
    for r in rows:
        r["next_inspection"] = compute_next_inspection(r.get("repair_date"), r.get("risk"))
    return render_template('all.html', rows=rows)

# === API Endpoints ===
@app.route('/api/udm/fittings/<uid>', methods=['GET'])
def get_fitting_api(uid):
    record = get_record_by_uid(uid)
    if not record:
        return jsonify({"error": "Fitting not found"}), 404
    record["next_inspection"] = compute_next_inspection(record.get("repair_date"), record.get("risk"))
    return jsonify(record)

@app.route('/api/udm/fittings/search', methods=['GET'])
def search_fittings_api():
    search_term = request.args.get('q', '')
    if not search_term:
        return jsonify({"error": "Search term required"}), 400
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT uid, item_type, vendor, risk
        FROM received 
        WHERE uid LIKE ? OR item_type LIKE ? OR vendor LIKE ?
        ORDER BY risk DESC, uid ASC
        LIMIT 20
    """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(results)

@app.route('/api/udm/fittings/<uid>/update', methods=['POST'])
def update_fitting_api(uid):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id FROM received WHERE uid = ?", (uid,))
    if not c.fetchone():
        conn.close()
        return jsonify({"error": "Fitting not found"}), 404
    update_fields, update_values = [], []
    if 'notes' in data:
        update_fields.append("notes = ?"); update_values.append(data['notes'])
    if 'risk' in data:
        update_fields.append("risk = ?"); update_values.append(data['risk'])
    if 'repair_date' in data:
        update_fields.append("repair_date = ?"); update_values.append(data['repair_date'])
    if not update_fields:
        conn.close(); return jsonify({"error": "No valid fields to update"}), 400
    update_values.append(uid)
    query = f"UPDATE received SET {', '.join(update_fields)} WHERE uid = ?"
    c.execute(query, update_values)
    conn.commit(); conn.close()
    return jsonify({"status": "success", "message": "Fitting updated successfully"})

@app.route('/api/tms/inspections', methods=['POST'])
def add_inspection():
    try:
        data = request.json
        if not data or 'uid' not in data:
            return jsonify({"error": "Missing UID or inspection data"}), 400
        uid = data['uid']
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM received WHERE uid = ?", (uid,))
        fitting = c.fetchone()
        if not fitting:
            conn.close(); return jsonify({"error": "Fitting not found"}), 404
        current_notes = fitting['notes'] or '[]'
        try:
            notes_list = eval(current_notes) if isinstance(current_notes, str) else current_notes
            if not isinstance(notes_list, list):
                notes_list = [{"note": current_notes, "date": "Unknown"}]
        except: notes_list = []
        inspection_data = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "technician": data.get('technician_id', 'unknown'),
            "condition": data.get('condition', ''),
            "observations": data.get('observations', ''),
            "severity": data.get('severity', 'Low'),
            "actions_taken": data.get('actions_taken', ''),
            "photos": data.get('photos', []),
            "location": data.get('location', {})
        }
        notes_list.append({"type": "inspection","data": inspection_data})
        current_risk = fitting['risk'] or 'Low'
        new_severity = data.get('severity', 'Low')
        risk_levels = {"Low": 0, "Medium": 1, "High": 2}
        current_level = risk_levels.get(current_risk, 0)
        new_level = risk_levels.get(new_severity, 0)
        final_risk = current_risk if new_level <= current_level else new_severity
        c.execute("""
            UPDATE received SET notes = ?, risk = ?, repair_date = ? WHERE uid = ?
        """, (str(notes_list), final_risk, datetime.now().strftime("%Y-%m-%d"), uid))
        c.execute("""
            INSERT INTO inspections (uid, inspection_date, condition, severity, technician, observations, actions_taken, photos, location_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get('condition', ''), data.get('severity', 'Low'),
            data.get('technician_id', 'unknown'),
            data.get('observations', ''), data.get('actions_taken', ''),
            str(data.get('photos', [])), str(data.get('location', {}))
        ))
        conn.commit(); conn.close()
        return jsonify({
            "status": "success",
            "message": "Inspection recorded successfully",
            "new_risk_level": final_risk,
            "next_inspection": compute_next_inspection(datetime.now().strftime("%Y-%m-%d"), final_risk)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to add inspection: {str(e)}"}), 500

@app.route('/api/tms/inspections/<uid>', methods=['GET'])
def get_inspections(uid):
    try:
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM inspections WHERE uid = ? ORDER BY inspection_date DESC", (uid,))
        inspections = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({"uid": uid,"inspections": inspections,"total_inspections": len(inspections)})
    except Exception as e:
        return jsonify({"error": f"Failed to get inspections: {str(e)}"}), 500

@app.route('/api/tms/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    try:
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        c = conn.cursor()
        total_fittings = c.execute("SELECT COUNT(*) FROM received").fetchone()[0]
        c.execute("SELECT risk, COUNT(*) as count FROM received GROUP BY risk")
        risk_stats = {row['risk']: row['count'] for row in c.fetchall()}
        c.execute("SELECT COUNT(*) FROM inspections WHERE inspection_date >= date('now', '-7 days')")
        recent_inspections = c.fetchone()[0]
        conn.close()
        return jsonify({
            "total_fittings": total_fittings,
            "risk_stats": risk_stats,
            "recent_inspections": recent_inspections
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        conn = sqlite3.connect(DB); conn.execute("SELECT 1"); conn.close()
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# === UDM Blueprint ===
udm_bp = Blueprint('udm', __name__, url_prefix="/udm", template_folder='templates')

@udm_bp.route('/')
def udm_home():
    rows = fetch_all_rows()
    for r in rows:
        r["next_inspection"] = compute_next_inspection(r.get("repair_date"), r.get("risk"))
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    c = conn.cursor(); c.execute("SELECT DISTINCT vendor FROM received WHERE vendor IS NOT NULL")
    vendors = [row['vendor'] for row in c.fetchall()]; conn.close()
    return render_template("udm.html", rows=rows, vendors=vendors, is_date_soon=is_date_soon)

# Extra JSON APIs inside UDM
@udm_bp.route('/api/fittings', methods=['GET'])
def api_get_fittings():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT uid, vendor, supply_date, warranty_end, repair_date, risk FROM received").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@udm_bp.route('/api/fitting/<uid>', methods=['GET'])
def api_get_fitting(uid):
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT uid, vendor, supply_date, warranty_end, repair_date, risk FROM received WHERE uid = ?", (uid,)).fetchone()
    conn.close(); 
    if not row: return jsonify({"error": "Fitting not found"}), 404
    return jsonify(dict(row))

@udm_bp.route('/api/fitting/<uid>', methods=['POST'])
def api_update_fitting_dates(uid):
    data = request.get_json()
    if not data: return jsonify({"error": "Missing request body"}), 400
    conn = sqlite3.connect(DB)
    conn.execute("""
        UPDATE received SET supply_date = ?, warranty_end = ?, repair_date = ? WHERE uid = ?
    """, (data.get("supply_date"), data.get("warranty_end"), data.get("repair_date"), uid))
    conn.commit(); conn.close()
    return jsonify({"status": "success", "message": "Fitting dates updated"})

# === TMS Blueprint ===
tms_bp = Blueprint('tms', __name__, url_prefix="/tms", template_folder='templates')

@tms_bp.route('/')
def tms_home():
    rows = fetch_all_rows()
    risk_stats = {
        'High': len([r for r in rows if r.get('risk') == 'High']),
        'Medium': len([r for r in rows if r.get('risk') == 'Medium']),
        'Low': len([r for r in rows if r.get('risk') == 'Low'])
    }
    high_risk_vendors = [r.get('vendor') for r in rows if r.get('vendor_risk') == 'High' and r.get('vendor')]
    return render_template("tms.html", rows=rows, risk_stats=risk_stats, high_risk_vendors=list(set(high_risk_vendors)))

# Extra JSON APIs inside TMS
@tms_bp.route('/api/risks', methods=['GET'])
def api_get_risks():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT uid, vendor, risk FROM received").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@tms_bp.route('/api/fitting/<uid>/risk', methods=['POST'])
def api_update_risk(uid):
    data = request.get_json()
    if not data or "risk" not in data: return jsonify({"error": "Missing risk field"}), 400
    new_risk = data["risk"]
    conn = sqlite3.connect(DB); conn.execute("UPDATE received SET risk = ? WHERE uid = ?", (new_risk, uid))
    conn.commit(); conn.close()
    return jsonify({"status": "success", "message": f"Risk updated to {new_risk}"})

@tms_bp.route('/api/fitting/<uid>/inspections', methods=['GET'])
def api_get_fitting_inspections(uid):
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM inspections WHERE uid = ? ORDER BY inspection_date DESC", (uid,)).fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@tms_bp.route('/api/fitting/<uid>/inspection', methods=['POST'])
def api_add_inspection(uid):
    data = request.get_json()
    if not data or "condition" not in data or "severity" not in data:
        return jsonify({"error": "Missing condition or severity"}), 400
    conn = sqlite3.connect(DB)
    conn.execute("""
        INSERT INTO inspections (uid, inspection_date, condition, severity, technician, observations, actions_taken, photos, location_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        uid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data.get("condition"), data.get("severity"),
        data.get("technician", "unknown"),
        data.get("observations", ""), data.get("actions_taken", ""),
        str(data.get("photos", [])), str(data.get("location", {}))
    ))
    conn.commit(); conn.close()
    return jsonify({"status": "success", "message": "Inspection added"})

# Register Blueprints
app.register_blueprint(udm_bp)
app.register_blueprint(tms_bp)

# === Home route ===
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Unified Portal - Indian Railways</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f8f9fa; font-family: 'Arial', sans-serif; padding: 50px 0; }
            .portal-card { border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }
            .portal-card:hover { transform: translateY(-5px); }
            .udm-card { border-top: 5px solid #0d6efd; }
            .tms-card { border-top: 5px solid #198754; }
            .header { background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%); color: white; padding: 30px 0;
                      margin-bottom: 40px; border-radius: 0 0 20px 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="container text-center">
                <h1 class="display-4">Indian Railways</h1>
                <p class="lead">Unified Portal System</p>
            </div>
        </div>
        <div class="container">
            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="card portal-card udm-card h-100">
                        <div class="card-body text-center">
                            <h3 class="card-title">UDM Portal</h3>
                            <p class="card-text">Date Management System</p>
                            <a href='/udm' class="btn btn-primary">Go to UDM</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="card portal-card tms-card h-100">
                        <div class="card-body text-center">
                            <h3 class="card-title">TMS Portal</h3>
                            <p class="card-text">Track Management System</p>
                            <a href='/tms' class="btn btn-success">Go to TMS</a>
                        </div>
                    </div>
                </div>
            </div>
            <div class="text-center mt-4">
                <a href="/all" class="btn btn-outline-secondary">View All Records</a>
                <a href="/api/health" class="btn btn-outline-info">API Health</a>
            </div>
            <div class="mt-5">
                <h4>API Endpoints:</h4>
                <div class="card"><div class="card-body">
                    <p><strong>GET</strong> /api/udm/fittings/&lt;uid&gt; - Get fitting details</p>
                    <p><strong>GET</strong> /api/udm/fittings/search?q=term - Search fittings</p>
                    <p><strong>POST</strong> /api/udm/fittings/&lt;uid&gt;/update - Update fitting</p>
                    <p><strong>POST</strong> /api/tms/inspections - Add inspection</p>
                    <p><strong>GET</strong> /api/tms/inspections/&lt;uid&gt; - Get inspections</p>
                    <p><strong>GET</strong> /api/tms/dashboard/stats - Get statistics</p>
                    <p><strong>GET</strong> /udm/api/fittings - All UDM fittings (JSON)</p>
                    <p><strong>POST</strong> /udm/api/fitting/&lt;uid&gt; - Update fitting dates</p>
                    <p><strong>GET</strong> /tms/api/risks - All risks (JSON)</p>
                    <p><strong>POST</strong> /tms/api/fitting/&lt;uid&gt;/risk - Update risk</p>
                    <p><strong>GET</strong> /tms/api/fitting/&lt;uid&gt;/inspections - Inspections for fitting</p>
                </div></div>
            </div>
        </div>
    </body>
    </html>
    """

# === Auto open browser ===
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5001/")

if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(debug=True, port=5001)
