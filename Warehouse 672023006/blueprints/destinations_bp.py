from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response
from bson import ObjectId
from common.mongo_connection import MongoConnection
from config import (
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE_WAREHOUSE_DESTINATIONS
)
from blueprints.auth_bp import login_required, role_required
from datetime import datetime
from common.utils import sanitize_text

destinations_bp = Blueprint("destinations", __name__, template_folder="../templates")

# === Koneksi MongoDB ===
mongodb_destinations = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_DESTINATIONS
)
destinations_col = mongodb_destinations.db["destinations"]

# === Route halaman destinations ===
@destinations_bp.route("/destinations")
@login_required
def list_destinations():
    return render_template("destinations.html")

# === API GET Semua Destination ===
@destinations_bp.route("/api/destinations")
@login_required
def get_destinations():
    dest_list = list(destinations_col.find())
    for d in dest_list:
        d["_id"] = str(d["_id"])
        if "is_active" not in d:
            d["is_active"] = 1
        d["is_active"] = 1 if d.get("is_active") else 0
    return jsonify(dest_list)

# === API GET Destination by ID ===
@destinations_bp.route("/api/destinations/<dest_id>")
@login_required
def get_destination(dest_id):
    try:
        oid = ObjectId(dest_id)
    except:
        return jsonify({"status": "error", "message": "Invalid ID"}), 400
    dest = destinations_col.find_one({"_id": oid})
    if not dest:
        return jsonify({"status": "error", "message": "Destination not found"}), 404
    dest["_id"] = str(dest["_id"])
    if "is_active" not in dest:
        dest["is_active"] = True
    return jsonify(dest)

# === API CREATE Destination ===
@destinations_bp.route("/api/destinations", methods=["POST"])
@login_required
@role_required("admin")
def create_destination():
    data = request.get_json() or {}
    name = sanitize_text(data.get("name", ""))
    contact = sanitize_text(data.get("contact", ""))
    address = sanitize_text(data.get("address", ""))
    destinations_col.insert_one({"name": name, "contact": contact, "address": address, "is_active": True})
    return jsonify({"status":"success"})

# === API UPDATE Destination ===
@destinations_bp.route("/api/destinations/<id>", methods=["PUT"])
@login_required
@role_required("admin")
def update_destination(id):
    data = request.json
    if "_id" in data:
        del data["_id"]
    oid = ObjectId(id)
    result = destinations_col.update_one({"_id": oid}, {"$set": data})
    if result.modified_count:
        return jsonify({"status": "success", "message": "Destination updated"})
    else:
        return jsonify({"status": "fail", "message": "No changes made"})

# === API DELETE Destination (soft delete) ===
@destinations_bp.route("/api/destinations/<dest_id>", methods=["DELETE"])
@login_required
@role_required("admin")
def delete_destination(dest_id):
    try:
        oid = ObjectId(dest_id)
    except:
        return jsonify({"status": "error", "message": "Invalid ID"}), 400
    destinations_col.update_one({"_id": oid}, {"$set": {"is_active": False}})
    return jsonify({"status": "success", "message": "Destination deleted (soft delete)."})

# === API untuk dropdown ===
@destinations_bp.route("/api/destinations/active")
@login_required 
def get_active_destinations():
    dests = list(destinations_col.find({"is_active": True}, {"_id": 1, "name": 1}))
    formatted = []
    for d in dests:
        formatted.append({
            "id": str(d["_id"]),
            "value": d["name"]  # This matches the template:#value# in the form
        })
    return jsonify(formatted)

@destinations_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = sanitize_text(request.form.get('username'))
        password = request.form.get('password')
        user = authenticate_user(username, password)
        if user:
            token = SessionManager.generate_token(**user)
            resp = make_response(redirect(url_for('dashboard.dashboard_page')))
            resp.set_cookie('token', token, httponly=True, samesite="Lax", max_age=24*60*60)
            return resp
        flash("Username atau password salah", "error")
    return render_template('login.html')
