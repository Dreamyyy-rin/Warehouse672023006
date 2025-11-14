from flask import Blueprint, request, jsonify, render_template
from bson import ObjectId
from common.mongo_connection import MongoConnection
from config import (
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE_WAREHOUSE_CATEGORIES
)
from blueprints.auth_bp import login_required, role_required
from datetime import datetime
from common.utils import sanitize_text

categories_bp = Blueprint("categories", __name__, template_folder="../templates")

# === Koneksi MongoDB ===
mongodb_categories = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_CATEGORIES
)
categories_col = mongodb_categories.db["categories"]

# === Render categories.html ===
@categories_bp.route("/categories")
@login_required
def list_categories():
    return render_template("categories.html")

# === API GET Semua Category (termasuk soft-deleted) ===
@categories_bp.route("/api/categories")
@login_required
def get_categories():
    cats = list(categories_col.find())  # tampilkan semua, is_active True/False
    for c in cats:
        c["_id"] = str(c["_id"])
        # pastikan is_active ada dan konversi ke 1/0
        if "is_active" not in c:
            c["is_active"] = 1
        c["is_active"] = 1 if c.get("is_active") else 0
    return jsonify(cats)

# === API GET Category by ID ===
@categories_bp.route("/api/categories/<category_id>")
@login_required
def get_category(category_id):
    try:
        oid = ObjectId(category_id)
    except:
        return jsonify({"status":"error","message":"Invalid ID"}), 400
    c = categories_col.find_one({"_id": oid})
    if not c:
        return jsonify({"status":"error","message":"Category not found"}), 404
    c["_id"] = str(c["_id"])
    if "is_active" not in c:
        c["is_active"] = True
    return jsonify(c)

# === API CREATE Category ===
@categories_bp.route("/api/categories", methods=["POST"])
@login_required
@role_required("admin")
def create_category():
    data = request.get_json() or {}
    name = sanitize_text(data.get("name", ""))
    desc = sanitize_text(data.get("description", ""))
    categories_col.insert_one({"name": name, "description": desc, "is_active": True})
    return jsonify({"status":"success","message":"Category added."})

# === API UPDATE Category ===
@categories_bp.route("/api/categories/<category_id>", methods=["PUT"])
@login_required
@role_required("admin")
def update_category(category_id):
    data = request.get_json()
    if "_id" in data:
        del data["_id"]  # jangan update _id
    try:
        oid = ObjectId(category_id)
    except:
        return jsonify({"status":"error","message":"Invalid ID"}), 400
    result = categories_col.update_one({"_id": oid}, {"$set": data})
    if result.modified_count:
        return jsonify({"status": "success", "message": "Category updated"})
    else:
        return jsonify({"status": "fail", "message": "No changes made"})

# === API DELETE Category (soft delete) ===
@categories_bp.route("/api/categories/<category_id>", methods=["DELETE"])
@login_required
@role_required("admin")
def delete_category(category_id):
    try:
        oid = ObjectId(category_id)
    except:
        return jsonify({"status":"error","message":"Invalid ID"}), 400
    # soft delete: is_active=False
    categories_col.update_one({"_id": oid}, {"$set": {"is_active": False}})
    return jsonify({"status":"success","message":"Category deleted (soft delete)."})

# Add this endpoint for active categories dropdown
@categories_bp.route("/api/categories/active")
@login_required
def get_active_categories():
    cats = list(categories_col.find({"is_active": True}, {"_id": 1, "name": 1}))
    formatted = [{"id": str(c["_id"]), "value": c.get("name", "")} for c in cats]
    return jsonify(formatted)
