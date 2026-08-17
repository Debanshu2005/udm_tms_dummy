from flask import Blueprint, render_template, current_app

udm_bp = Blueprint('udm', __name__, url_prefix="/udm", template_folder='../templates')

@udm_bp.route('/')
def udm_home():
    # Fetch all rows from app.py
    rows = current_app.fetch_all_rows()
    
    # Add next inspection date
    for r in rows:
        r["next_inspection"] = current_app.compute_next_inspection(
            r.get("repair_date"),
            r.get("risk")
        )
    
    # Pass only relevant fields to template
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
