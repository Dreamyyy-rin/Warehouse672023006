from flask import Blueprint, render_template, jsonify
from datetime import datetime, timedelta
from common.mongo_connection import MongoConnection
from config import MONGODB_CONNECTION_STRING, MONGODB_DATABASE_WAREHOUSE_ITEMS, MONGODB_DATABASE_WAREHOUSE_TRANSACTIONS, MONGODB_COLLECTION_TRANSACTIONS
from blueprints.auth_bp import login_required

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates")

# koneksi ke DB
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


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_page():
    return render_template("dashboard.html")


@dashboard_bp.route("/api/dashboard/summary")
@login_required
def api_dashboard_summary():
    total_items = items_col.count_documents({})

    # Fix today's transactions count
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_str = today_start.strftime("%d-%m-%Y")
    
    # Count transactions with today's date prefix
    today_trans = transactions_col.count_documents({
        "timestamp": {"$regex": f"^{today_start_str}"}
    })

    # Rest of aggregation for low stock
    pipeline = [
        {"$group": {
            "_id": "$item_id",
            "total_in": {"$sum": {"$cond": [{"$eq": ["$type", "in"]}, "$quantity", 0]}},
            "total_out": {"$sum": {"$cond": [{"$eq": ["$type", "out"]}, "$quantity", 0]}}
        }}
    ]
    agg = list(transactions_col.aggregate(pipeline))
    stock_map = {}
    for a in agg:
        k = str(a["_id"])
        stock_map[k] = (a.get("total_in") or 0) - (a.get("total_out") or 0)

    low_stock = 0
    for it in items_col.find({}, {"_id": 1}):
        sid = str(it["_id"])
        s = stock_map.get(sid, 0)
        if s < 10:
            low_stock += 1

    return jsonify({
        "total_items": total_items,
        "low_stock": low_stock,
        "today_trans": today_trans
    })


@dashboard_bp.route("/api/dashboard/chart_data")
@login_required
def api_dashboard_chart_data():
    data = list(transactions_col.find({"status":"active"}))
    # hitung jumlah transaksi per tanggal
    counts = {}
    for t in data:
        ts = t.get("timestamp")
        if isinstance(ts, str):
            date = ts.split(" ")[0]  # ambil "27-10-2025"
        elif isinstance(ts, datetime):
            date = ts.strftime("%d-%m-%Y")
        else:
            continue
        counts[date] = counts.get(date, 0) + 1
    # sort by date
    sorted_dates = sorted(counts.keys(), key=lambda d: datetime.strptime(d, "%d-%m-%Y"))
    result = [{"date": d, "count": counts[d]} for d in sorted_dates]
    return jsonify(result)


@dashboard_bp.route("/api/dashboard/low_stock")
@login_required
def get_low_stock_items():
    LOW_STOCK_THRESHOLD = 10
    low_stock = []
    
    items = items_col.find({})
    for item in items:
        stock = int(item.get('stock', 0))
        if stock < LOW_STOCK_THRESHOLD:
            low_stock.append({
                'name': item.get('name'),
                'stock': stock,
                'supplier': item.get('supplier', {}).get('name', '-')
            })
            
    return jsonify(low_stock)
