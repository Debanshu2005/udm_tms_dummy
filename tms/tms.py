from flask import Blueprint, render_template, current_app

tms_bp = Blueprint('tms', __name__, url_prefix="/tms", template_folder='../templates')

@tms_bp.route('/')
def tms_home():
    # Fetch all rows from app.py
    rows = current_app.fetch_all_rows()
    
    # Pass only relevant fields for TMS
    tms_rows = [
        {
            "uid": r["uid"],
            "item_type": r["item_type"],
            "risk": r["risk"],
            "vendor_risk": r["vendor_risk"]
        } for r in rows
    ]
    
    return render_template("tms.html", rows=tms_rows)
