from flask import Blueprint, render_template, request, jsonify
from bson import ObjectId
from datetime import datetime
from common.mongo_connection import MongoConnection
from config import (
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE_WAREHOUSE_USERS
)
from blueprints.auth_bp import login_required, role_required
from werkzeug.security import generate_password_hash
from common.utils import sanitize_text

users_bp = Blueprint("users", __name__, template_folder="../templates")

# MongoDB connection
mongodb = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_USERS
)
users_col = mongodb.db["users"]

@users_bp.route("/users")
@login_required
@role_required("admin")
def users_page():
    return render_template("users.html")

@users_bp.route("/api/users")
@login_required
@role_required("admin")
def get_users():
    users = list(users_col.find({}, {"password": 0}))  # exclude password
    for u in users:
        u["_id"] = str(u["_id"])
        if "created_at" in u:
            u["created_at"] = u["created_at"].strftime("%d-%m-%Y %H:%M")
    return jsonify(users)

@users_bp.route("/api/users", methods=["POST"])
@login_required
@role_required("admin")
def create_user():
    data = request.get_json()
    username = sanitize_text(data.get("username", ""))
    password = data.get("password", "")
    role = sanitize_text(data.get("role", "user")).lower()
    
    # Validation
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required"}), 400
    
    # Check username unique
    if users_col.find_one({"username": username}):
        return jsonify({"status": "error", "message": "Username already exists"}), 400
    
    # Validate role
    valid_roles = ["admin", "manager", "staff"]
    if role not in valid_roles:
        return jsonify({"status": "error", "message": "Invalid role"}), 400

    # Create user
    user_doc = {
        "username": username,
        "password": generate_password_hash(password),
        "role": role,
        "created_at": datetime.utcnow()
    }
    users_col.insert_one(user_doc)
    return jsonify({"status": "success", "message": "User created successfully"})

@users_bp.route("/api/users/<user_id>", methods=["DELETE"])
@login_required
@role_required("admin")
def delete_user(user_id):
    try:
        oid = ObjectId(user_id)
    except:
        return jsonify({"status": "error", "message": "Invalid user ID"}), 400
        
    # Don't allow deleting self
    token_data = g.user
    user = users_col.find_one({"_id": oid})
    if user and user["username"] == token_data["username"]:
        return jsonify({"status": "error", "message": "Cannot delete yourself"}), 400
        
    users_col.delete_one({"_id": oid})
    return jsonify({"status": "success", "message": "User deleted"})