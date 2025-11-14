from flask import Blueprint, render_template, request, redirect, url_for, make_response, flash, jsonify, g
from common.session_manager import SessionManager
from common.mongo_connection import MongoConnection
from config import (
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE_WAREHOUSE_USERS,
    MONGODB_COLLECTION_USERS,
    MONGODB_COLLECTION_SESSIONS
)
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta
from common.utils import sanitize_text
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re

auth_bp = Blueprint("auth", __name__, template_folder="../templates")

# MongoDB connection for users & sessions
mongodb = MongoConnection(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DATABASE_WAREHOUSE_USERS
)
users_col = mongodb.db[MONGODB_COLLECTION_USERS]
sessions_col = mongodb.db[MONGODB_COLLECTION_SESSIONS]

SessionManager = SessionManager()

limiter = Limiter(
    app=None,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# === Helper ===
def authenticate_user(username, password):
    """Validate username/password against users_col (password hashed)."""
    if not username or not password:
        return None
    u = users_col.find_one({"username": username})
    if not u:
        return None
    hashed = u.get("password", "")
    if check_password_hash(hashed, password):
        return {"username": u.get("username"), "role": u.get("role", "user")}
    return None

def create_server_session(user_id):
    """Optional server-side session record (not required if SessionManager manages tokens)."""
    token = str(uuid.uuid4())
    sessions_col.insert_one({
        "user_id": user_id,
        "token": token,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=1)
    })
    return token

# === LOGIN (GET/POST) ===
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute") # Prevent brute force
def login():
    if request.method == "POST":
        username = sanitize_text(request.form.get('username'))
        password = request.form.get('password')
        
        # Get user from database
        user = users_col.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            # Create token with proper role
            token = SessionManager.generate_token(
                username=user["username"],
                role=user["role"]
            )
            
            # Set cookie and redirect
            resp = make_response(redirect(url_for('dashboard.dashboard_page')))
            resp.set_cookie(
                'token', 
                token, 
                httponly=True, 
                samesite="Lax",
                max_age=24*60*60  # 1 day
            )
            print(f"Logging in user: {user['username']} with role: {user['role']}")
            return resp
            
        flash("Username atau password salah", "error")
    return render_template('login.html')


# === LOGOUT ===
@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    token = request.cookies.get('token')
    if token:
        try:
            SessionManager.delete_token(token)
        except Exception:
            pass
    response = make_response(redirect(url_for('auth.login')))
    response.delete_cookie('token')
    flash("Logout berhasil!", "success")
    return response


# === LOGIN REQUIRED ===
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            flash("Anda harus login terlebih dahulu", "warning")
            return redirect(url_for('auth.login'))
        user = SessionManager.verify_token(token)
        if not user:
            flash("Sesi login anda sudah habis, silakan login ulang", "warning")
            resp = make_response(redirect(url_for('auth.login')))
            resp.delete_cookie('token')
            return resp
        # set g.user for downstream handlers
        g.user = user
        return f(*args, **kwargs)
    return decorated_function


# === ROLE REQUIRED ===
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.cookies.get('token')
            if not token:
                flash("Anda harus login terlebih dahulu", "warning")
                return redirect(url_for('auth.login'))
            session_data = SessionManager.verify_token(token)
            if not session_data:
                resp = make_response(redirect(url_for('auth.login')))
                resp.delete_cookie('token')
                return resp
            # role comparison (case-insensitive)
            user_role = (session_data.get('role') or "").lower()
            allowed = [r.lower() for r in allowed_roles]
            if user_role not in allowed:
                return jsonify({"message": "Anda tidak memiliki akses ke halaman ini"}), 403
            g.user = session_data
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# === API: Info user dari token ===
@auth_bp.route('/api/user/info')
@login_required  # Keep this decorator
def api_user_info():
    token = request.cookies.get('token')
    if not token:
        return jsonify({
            "username": "Guest",
            "role": "guest"
        }), 200  # Return 200 even for guest
        
    user_data = SessionManager.verify_token(token)
    if not user_data:
        return jsonify({
            "username": "Guest",
            "role": "guest"
        }), 200  # Return 200 even for invalid token
    
    return jsonify({
        "username": user_data["username"],
        "role": user_data["role"]
    }), 200


# === CREATE USER (admin) ===
@auth_bp.route("/users", methods=["POST"])
@login_required
@role_required("admin")
def create_user():
    data = request.get_json() or {}
    username = sanitize_text(data.get("username", ""))
    password = data.get("password", "")
    role = sanitize_text(data.get("role", "user"))
    if not username or not password:
        return jsonify({"status":"error","message":"Username/password wajib."}), 400
    hashed = generate_password_hash(password)
    users_col.insert_one({"username": username, "password": hashed, "role": role, "created_at": datetime.utcnow()})
    return jsonify({"status":"success"})

# In auth_bp.py add these roles
ROLE_PERMISSIONS = {
    'admin': ['all'],
    'manager': ['items', 'transactions', 'suppliers', 'categories', 'destinations'],
    'staff': ['transactions']
}

def has_permission(user_role, resource):
    """Check if role has permission to access resource"""
    if not user_role or not resource:
        return False
    allowed = ROLE_PERMISSIONS.get(user_role.lower(), [])
    return 'all' in allowed or resource in allowed

@auth_bp.route('/api/check_permission/<resource>')
@login_required
def check_permission(resource):
    user = g.user
    if not user:
        return jsonify({'allowed': False})
    return jsonify({
        'allowed': has_permission(user.get('role'), resource)
    })

def check_menu_access(menu, role):
    menu_permissions = {
        'admin': ['dashboard', 'items', 'transactions', 'suppliers', 'categories', 'destinations', 'users'],
        'manager': ['dashboard', 'items', 'transactions', 'suppliers', 'categories', 'destinations'],
        'staff': ['dashboard', 'transactions']
    }
    allowed = menu_permissions.get(role.lower(), [])
    return menu in allowed

@auth_bp.before_request
def check_route_permission():
    # Skip for login/logout routes and api/user/info
    if request.endpoint in ['auth.login', 'auth.logout', 'auth.api_user_info']:
        return
        
    token = request.cookies.get('token')
    if token:
        user = SessionManager.verify_token(token)
        if user:
            # Get menu from route
            path = request.path.split('/')
            if len(path) > 1:
                menu = path[1]  # e.g. /items -> items
                if menu and not check_menu_access(menu, user.get('role', '')):
                    return jsonify({
                        "status": "error",
                        "message": "You don't have permission to access this page"
                    }), 403

def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search("[0-9]", password):
        return False
    if not re.search("[A-Z]", password):
        return False
    if not re.search("[a-z]", password):
        return False
    return True
