from flask import Blueprint, request, jsonify, render_template
from bson import ObjectId
from common.mongo_connection import MongoConnection
from config import (
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE_WAREHOUSE_SUPPLIERS
)
from blueprints.auth_bp import login_required, role_required
from datetime import datetime
from common.utils import sanitize_text

suppliers_bp = Blueprint("suppliers", __name__, template_folder="../templates")

# === Koneksi MongoDB ===
mongodb_suppliers = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_SUPPLIERS
)
suppliers_col = mongodb_suppliers.db["suppliers"]

# === Route halaman suppliers ===
@suppliers_bp.route("/suppliers")
@login_required
def list_suppliers():
    return render_template("suppliers.html")

# === API GET Semua Supplier ===
@suppliers_bp.route("/api/suppliers")
@login_required
def get_suppliers():
    sup_list = list(suppliers_col.find())
    # ubah _id jadi string
    for s in sup_list:
        s["_id"] = str(s["_id"])
        # pastikan ada is_active dan konversi ke boolean yang benar
        if "is_active" not in s:
            s["is_active"] = True
        s["is_active"] = True if s.get("is_active") else False
    return jsonify(sup_list)

# === API GET Supplier by ID ===
@suppliers_bp.route("/api/suppliers/<supplier_id>")
@login_required
def get_supplier(supplier_id):
    try:
        oid = ObjectId(supplier_id)
    except:
        return jsonify({"status":"error","message":"Invalid ID"}), 400
    sup = suppliers_col.find_one({"_id": oid})
    if not sup:
        return jsonify({"status":"error","message":"Supplier not found"}), 404
    sup["_id"] = str(sup["_id"])
    if "is_active" not in sup:
        sup["is_active"] = True
    return jsonify(sup)

# === API CREATE Supplier ===
@suppliers_bp.route("/api/suppliers", methods=["POST"])
@login_required
@role_required("admin")
def create_supplier():
    data = request.get_json() or {}
    name = sanitize_text(data.get("name", ""))
    contact = sanitize_text(data.get("contact", ""))
    address = sanitize_text(data.get("address", ""))
    doc = {"name": name, "contact": contact, "address": address, "is_active": True}
    suppliers_col.insert_one(doc)
    return jsonify({"status":"success"})

# === API UPDATE Supplier ===
@suppliers_bp.route("/api/suppliers/<id>", methods=["PUT"])
@login_required
@role_required("admin")
def update_supplier(id):
    data = request.json
    if "_id" in data:
        del data["_id"]  # jangan update _id
    oid = ObjectId(id)
    result = suppliers_col.update_one({"_id": oid}, {"$set": data})
    if result.modified_count:
        return jsonify({"status": "success", "message": "Supplier updated"})
    else:
        return jsonify({"status": "fail", "message": "No changes made"})

# === API DELETE Supplier (soft delete) ===
@suppliers_bp.route("/api/suppliers/<supplier_id>", methods=["DELETE"])
@login_required
@role_required("admin")
def delete_supplier(supplier_id):
    try:
        oid = ObjectId(supplier_id)
    except:
        return jsonify({"status":"error","message":"Invalid ID"}), 400
    suppliers_col.update_one({"_id": oid}, {"$set": {"is_active": False}})
    return jsonify({"status":"success","message":"Supplier deleted (soft delete)."})

# Add this endpoint for active suppliers dropdown
@suppliers_bp.route("/api/suppliers/active")
@login_required
def get_active_suppliers():
    suppliers = list(suppliers_col.find({"is_active": True}, {"_id": 1, "name": 1}))
    formatted = [{"id": str(s["_id"]), "value": s.get("name", "")} for s in suppliers]
    return jsonify(formatted)
