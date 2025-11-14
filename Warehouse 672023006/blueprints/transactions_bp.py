from flask import Blueprint, render_template, request, jsonify, g
from bson import ObjectId
from datetime import datetime, timedelta
from common.utils import sanitize_text, to_int

from common.mongo_connection import MongoConnection
from config import (
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE_WAREHOUSE_ITEMS,
    MONGODB_DATABASE_WAREHOUSE_TRANSACTIONS,
    MONGODB_DATABASE_WAREHOUSE_SUPPLIERS,
    MONGODB_DATABASE_WAREHOUSE_DESTINATIONS
    
)
from blueprints.auth_bp import login_required, role_required
from datetime import datetime, timedelta
import pymongo

transactions_bp = Blueprint("transactions", __name__, template_folder="../templates")

# === Koneksi ke database ===
mongodb_items = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_ITEMS
)
items_col = mongodb_items.db["items"]

mongodb_transactions = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_TRANSACTIONS
)
transactions_col = mongodb_transactions.db["transactions"]

mongodb_suppliers = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_SUPPLIERS
)
mongodb_destinations = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_DESTINATIONS
)
destinations_col = mongodb_destinations.db["destinations"]
# === HALAMAN ===
@transactions_bp.route("/transactions")
@login_required
def transactions_page():
    """Halaman riwayat transaksi"""
    return render_template("transactions.html")

@transactions_bp.route("/transactions/in")
@login_required
@role_required("admin")
def barang_masuk_page():
    return render_template("barang_masuk.html")

@transactions_bp.route("/transactions/out")
@login_required
def barang_keluar_page():
    return render_template("barang_keluar.html")

# === API ===
@transactions_bp.route("/api/transactions/search_items")
@login_required
def api_search_items():
    query = request.args.get("filter[value]", "")
    matched = items_col.find(
        {"name": {"$regex": query, "$options": "i"}, "is_active": {"$ne": False}},
        {"_id": 1, "name": 1, "price": 1}
    )
    items = matched if isinstance(matched, list) else list(matched)
    options = [
        {
            "id": str(item["_id"]),
            "value": item["name"],
            "price": float(item.get("price", 0))
        }
        for item in items
    ]
    return jsonify(options)


# Update the history API pipeline
@transactions_bp.route("/api/transactions/history")
@login_required
def api_riwayat_transaksi():
    docs = list(transactions_col.find().sort([("_id", -1)]))
    out = []
    for t in docs:
        details = "-"
        if t.get("type") == "in":
            details = t.get("supplier_name", "-")
        else:
            details = t.get("destination_name", "-")
            if not details or details == "-":
                try:
                    dest_id = t.get("destination_id")
                    if dest_id:
                        dest = destinations_col.find_one({"_id": dest_id})
                        if dest:
                            details = dest.get("name", "-")
                except:
                    pass
        
        out.append({
            "_id": str(t["_id"]),
            "timestamp": t.get("timestamp"),
            "item_name": t.get("item_name", "-"),
            "type": t.get("type", "in"),
            "quantity": int(t.get("quantity", 0)),
            "details_name": details,
            "cost": float(t.get("transaction_cost", 0)),
            "status": t.get("status", "active")
        })
    return jsonify(out)

@transactions_bp.route("/api/transactions/cancel/<tx_id>", methods=["POST"])
@login_required
@role_required("admin")
def api_cancel_transaction(tx_id):
    try:
        oid = ObjectId(tx_id)
    except:
        return jsonify({"status":"error","message":"Invalid transaction ID"}), 400

    tx = transactions_col.find_one({"_id": oid})
    if not tx:
        return jsonify({"status":"error","message":"Transaction not found"}), 404

    if tx.get("status") in ("canceled", "returned"):
        return jsonify({"status":"error","message":"Transaction already canceled/returned"}), 400

    item_id = tx.get("item_id")
    quantity = tx.get("quantity", 0)
    
    # Update stock based on transaction type
    if tx.get("type") == "in":
        # If canceling IN transaction, decrease stock
        items_col.update_one(
            {"_id": item_id}, 
            {"$inc": {"stock": -quantity}}
        )
    else:
        # If canceling OUT transaction, increase stock
        items_col.update_one(
            {"_id": item_id}, 
            {"$inc": {"stock": quantity}}
        )

    # Mark as canceled
    transactions_col.update_one(
        {"_id": oid}, 
        {
            "$set": {
                "status": "canceled",
                "canceled_at": datetime.utcnow() + timedelta(hours=7)
            }
        }
    )

    return jsonify({"status":"success","message":"Transaction canceled and stock updated."})

@transactions_bp.route("/api/transactions/return/<tx_id>", methods=["POST"])
@login_required
def api_return_transaction(tx_id):
    try:
        oid = ObjectId(tx_id)
    except:
        return jsonify({"status":"error","message":"Invalid transaction ID"}), 400

    tx = transactions_col.find_one({"_id": oid})
    if not tx:
        return jsonify({"status":"error","message":"Transaction not found"}), 404

    if tx.get("type") != "out":
        return jsonify({"status":"error","message":"Only OUT transactions can be returned"}), 400

    if tx.get("status") in ("canceled", "returned"):
        return jsonify({"status":"error","message":"Transaction already canceled/returned"}), 400

    item_id = tx.get("item_id")
    quantity = tx.get("quantity", 0)

    # Return adds stock back
    items_col.update_one(
        {"_id": item_id}, 
        {"$inc": {"stock": quantity}}
    )

    # Mark as returned
    transactions_col.update_one(
        {"_id": oid}, 
        {
            "$set": {
                "status": "returned",
                "returned_at": datetime.utcnow() + timedelta(hours=7)
            }
        }
    )

    return jsonify({"status":"success","message":"Transaction returned and stock updated."})

# === Helper ===
def compute_stock_for_item(item_oid):
    """Hitung stok saat ini berdasarkan transaksi"""
    try:
        oid = ObjectId(item_oid) if not isinstance(item_oid, ObjectId) else item_oid
    except Exception:
        return 0
    pipeline = [
        {"$match": {"item_id": oid}},
        {"$group": {
            "_id": "$item_id",
            "total_in": {"$sum": {"$cond": [{"$eq": ["$type", "in"]}, "$quantity", 0]}},
            "total_out": {"$sum": {"$cond": [{"$eq": ["$type", "out"]}, "$quantity", 0]}}
        }}
    ]
    agg = list(transactions_col.aggregate(pipeline))
    if not agg:
        return 0
    a = agg[0]
    return (a.get("total_in") or 0) - (a.get("total_out") or 0)

# === Barang Masuk ===
@transactions_bp.route("/api/transactions/in", methods=["POST"])
@login_required
@role_required("admin")
def api_barang_masuk():
    data = request.get_json()
    item_id_str = data.get("item_id")
    quantity = int(data.get("quantity", 0))

    if not item_id_str or quantity <= 0:
        return jsonify({"status": "error", "message": "Data tidak valid."}), 400

    item_id = ObjectId(item_id_str)
    item = items_col.find_one({"_id": item_id})

    if not item:
        return jsonify({"status": "error", "message": "Item tidak ditemukan."}), 404

    # Tidak boleh masuk jika item nonaktif
    if not item.get("is_active", True):
        return jsonify({"status": "error", "message": "Item sudah nonaktif."}), 400

    price = float(item.get("price", 0))
    cost = quantity * price

    supplier = item.get("supplier", {})
    supplier_name = supplier.get("name", "-")

    transaction_doc = {
        "item_id": item_id,
        "item_name": item.get("name", "N/A"),
        "type": "in",
        "quantity": quantity,
        "transaction_cost": cost,
        "supplier_name": supplier_name,
        "timestamp": (datetime.utcnow()+timedelta(hours=7)).strftime("%d-%m-%Y %H:%M"),
        "status": "active"
    }

    transactions_col.insert_one(transaction_doc)

    # ✅ update stock item
    items_col.update_one({"_id": item_id}, {"$inc": {"stock": quantity}})

    return jsonify({
        "status": "success",
        "message": f"Barang masuk: +{quantity} ke {item.get('name')}",
        "cost": cost
    })


def _to_objectid(maybe):
    """Terima string, dict {"id": "..."} atau dict {"$oid": "..."} atau ObjectId."""
    if not maybe:
        return None
    if isinstance(maybe, ObjectId):
        return maybe
    if isinstance(maybe, dict):
        for key in ("$oid", "id", "_id"):
            if key in maybe and maybe[key]:
                maybe = maybe[key]
                break
    if isinstance(maybe, str):
        s = maybe.strip()
        if s in ("", "-", "null", "None"):
            return None
        try:
            return ObjectId(s)
        except Exception:
            return None
    return None

@transactions_bp.route("/api/transactions/out", methods=["POST"])
@login_required
def api_barang_keluar():
    data = request.get_json() or {}
    item_raw = data.get("item_id") or data.get("item")
    dest_raw = data.get("destination_id") or data.get("destination")
    qty = to_int(data.get("quantity"), default=None)
    if qty is None or qty <= 0:
        return jsonify({"status":"error","message":"Quantity tidak valid."}), 400

    item_oid = _to_objectid(item_raw)
    if not item_oid:
        return jsonify({"status":"error","message":"Invalid item id format."}), 400

    dest_oid = _to_objectid(dest_raw)

    item = items_col.find_one({"_id": item_oid})
    if not item:
        return jsonify({"status":"error","message":"Item tidak ditemukan."}), 404

    current_stock = int(item.get("stock", 0))
    if current_stock < qty:
        return jsonify({"status":"error","message":f"Stok tidak cukup: {current_stock}"}), 400

    destination_name = "-"
    if dest_oid:
        d = destinations_col.find_one({"_id": dest_oid})
        if d:
            destination_name = d.get("name", "-")

    txn = {
        "item_id": item_oid,
        "item_name": item.get("name", ""),
        "type": "out",
        "quantity": qty,
        "transaction_cost": float(item.get("price", 0)) * qty,
        "destination_id": dest_oid,   # ObjectId or None
        "destination_name": destination_name,
        "timestamp": (datetime.utcnow() + timedelta(hours=7)).strftime("%d-%m-%Y %H:%M"),
        "status": "active",
        "performed_by": g.user.get("username") if getattr(g, "user", None) else None
    }

    items_col.update_one({"_id": item_oid}, {"$inc": {"stock": -qty}})
    transactions_col.insert_one(txn)
    return jsonify({"status":"success","message":"Barang keluar berhasil."})
