from flask import Blueprint, render_template, request, jsonify
from bson import ObjectId
from common.mongo_connection import MongoConnection
from config import (
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE_WAREHOUSE_ITEMS,
    MONGODB_DATABASE_WAREHOUSE_CATEGORIES,
    MONGODB_DATABASE_WAREHOUSE_SUPPLIERS,
    MONGODB_COLLECTION_ITEMS,
    MONGODB_COLLECTION_CATEGORIES,
    MONGODB_COLLECTION_SUPPLIERS,
    MONGODB_DATABASE_WAREHOUSE_TRANSACTIONS,
    MONGODB_COLLECTION_TRANSACTIONS
)
from blueprints.auth_bp import login_required, role_required
from datetime import datetime, timedelta

items_bp = Blueprint("items", __name__, template_folder="../templates")

mongodbitems = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_ITEMS
)

mongodbcategories = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_CATEGORIES
)

mongodbsuppliers = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_SUPPLIERS
)

# connection to transactions DB to compute stock
mongodb_transactions = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_TRANSACTIONS
)

items_col = mongodbitems.db[MONGODB_COLLECTION_ITEMS]
categories_col = mongodbcategories.db[MONGODB_COLLECTION_CATEGORIES]
suppliers_col = mongodbsuppliers.db[MONGODB_COLLECTION_SUPPLIERS]
transactions_col = mongodb_transactions.db[MONGODB_COLLECTION_TRANSACTIONS]


def normalize_oid(value):
    if value is None:
        return None
    try:
        if isinstance(value, ObjectId):
            return str(value)
    except Exception:
        pass
    if isinstance(value, dict):
        if "$oid" in value:
            return value["$oid"]
        if "_id" in value:
            inner = value["_id"]
            if isinstance(inner, ObjectId):
                return str(inner)
            else:
                return str(inner)
        if "id" in value:
            return str(value["id"])
        return None
    if isinstance(value, str):
        return value
    return None


# ===== View page =====
@items_bp.route("/items")
@login_required
def list_items():
    return render_template("items.html")


# ===== API: get all items (with dynamic stock computed from transactions) =====
@items_bp.route("/api/items")
@login_required
def api_get_items():
    docs = list(items_col.find())
    out = []
    for d in docs:
        out.append({
            "_id": str(d["_id"]),
            "name": d.get("name", ""),
            "stock": d.get("stock", 0),
            "price": float(d.get("price", 0)),
            "category_name": d.get("category", {}).get("name", "-"),
            "supplier_name": d.get("supplier", {}).get("name", "-"),
            "is_active": d.get("is_active", True)  # Default to True if not set
        })
    return jsonify(out)


# ===== API: add item =====
@items_bp.route("/items/add", methods=["POST"])
@login_required
@role_required("admin")
def api_add_item():
    # support JSON body (from new items.html) or form data (fallback)
    data = request.get_json(silent=True) or request.form or {}

    raw_cat = data.get("category_id") or data.get("category")
    raw_sup = data.get("supplier_id") or data.get("supplier")
    cat_obj = None
    sup_obj = None

    # resolve category object
    if raw_cat:
        try:
            cat_obj = categories_col.find_one({"_id": ObjectId(raw_cat)})
        except Exception:
            cat_obj = None

    # resolve supplier object
    if raw_sup:
        try:
            sup_obj = suppliers_col.find_one({"_id": ObjectId(raw_sup)})
        except Exception:
            sup_obj = None

    # name and price - be robust if price is string
    name = data.get("name") or ""
    try:
        price = float(data.get("price") or 0)
    except Exception:
        price = 0.0

    item = {
        "name": name,
        # stock is computed from transactions elsewhere
        "price": price,
        "category": {"_id": cat_obj["_id"], "name": cat_obj["name"]} if cat_obj else None,
        "supplier": {"_id": sup_obj["_id"], "name": sup_obj["name"]} if sup_obj else None,
        # created_at keep consistent format
        "created_at": (datetime.utcnow()+timedelta(hours=7)).strftime("%d-%m-%Y %H.%M"),
        "is_active": True
    }

    items_col.insert_one(item)
    return jsonify({"status": "success", "message": "Item added", "item_id": str(item.get("_id", ""))})



# ===== API: edit item =====
@items_bp.route("/items/edit/<item_id>", methods=["POST"])
@login_required
@role_required("admin")
def api_edit_item(item_id):
    data = request.get_json(silent=True) or request.form or {}

    update_doc = {}
    # name
    if "name" in data:
        update_doc["name"] = data.get("name") or ""
    # price
    if "price" in data:
        try:
            update_doc["price"] = float(data.get("price") or 0)
        except Exception:
            update_doc["price"] = 0.0

    # category
    raw_cat = data.get("category_id") or data.get("category")
    if raw_cat:
        try:
            cat_obj = categories_col.find_one({"_id": ObjectId(raw_cat)})
            if cat_obj:
                update_doc["category"] = {"_id": cat_obj["_id"], "name": cat_obj["name"]}
            else:
                update_doc["category"] = None
        except Exception:
            update_doc["category"] = None
    else:
        # explicitly allow clearing category if empty string passed
        if "category_id" in data or "category" in data:
            update_doc["category"] = None

    # supplier
    raw_sup = data.get("supplier_id") or data.get("supplier")
    if raw_sup:
        try:
            sup_obj = suppliers_col.find_one({"_id": ObjectId(raw_sup)})
            if sup_obj:
                update_doc["supplier"] = {"_id": sup_obj["_id"], "name": sup_obj["name"]}
            else:
                update_doc["supplier"] = None
        except Exception:
            update_doc["supplier"] = None
    else:
        if "supplier_id" in data or "supplier" in data:
            update_doc["supplier"] = None

    # do update (only fields present)
    if update_doc:
        items_col.update_one({"_id": ObjectId(item_id)}, {"$set": update_doc})

    return jsonify({"status": "success", "message": "Item updated"})


# ===== API: deactivate item (soft-delete) =====
# ===== API: deactivate item (soft-delete) =====
@items_bp.route("/items/deactivate/<item_id>", methods=["POST"])
@login_required
@role_required("admin")
def api_deactivate_item(item_id):
    try:
        oid = ObjectId(item_id)
    except Exception:
        return jsonify({"status":"error","message":"Invalid item id"}), 400

    # Cuma update status, jangan edit nama!
    items_col.update_one({"_id": oid}, {"$set": {"is_active": False}})
    return jsonify({"status":"success","message":"Item marked as inactive"})


# Add new endpoint for item history

@items_bp.route("/api/items/<item_id>/history")
@login_required
def get_item_history(item_id):
    try:
        item_oid = ObjectId(item_id)
    except:
        return jsonify({"status":"error", "message":"Invalid item ID"}), 400
        
    # Get item details
    item = items_col.find_one({"_id": item_oid})
    if not item:
        return jsonify({"status":"error", "message":"Item not found"}), 404
        
    # Get transaction history
    history = list(transactions_col.find(
        {"item_id": item_oid},
        {"_id": 0, "timestamp": 1, "type": 1, "quantity": 1, 
         "supplier_name": 1, "destination_name": 1}
    ).sort("timestamp", -1))
    
    # Format history entries
    formatted = []
    for h in history:
        details = h.get("supplier_name") if h["type"] == "in" else h.get("destination_name")
        formatted.append({
            "timestamp": h["timestamp"],
            "type": "Masuk" if h["type"] == "in" else "Keluar",
            "quantity": h["quantity"],
            "details_name": details or "-"
        })
        
    return jsonify(formatted)

