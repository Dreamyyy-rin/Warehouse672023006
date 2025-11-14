from flask import Flask, redirect, url_for, request
from blueprints.auth_bp import auth_bp
from blueprints.items_bp import items_bp
from blueprints.transactions_bp import transactions_bp
from blueprints.dashboard_bp import dashboard_bp
from blueprints.category_bp import categories_bp
from blueprints.supplier_bp import suppliers_bp
from blueprints.destinations_bp import destinations_bp
from blueprints.users_bp import users_bp
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "secret_key_kapita_2025"

# Basic config
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1)
)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(items_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(categories_bp)
app.register_blueprint(suppliers_bp)
app.register_blueprint(destinations_bp)
app.register_blueprint(users_bp)

@app.route('/')
def index():
    token = request.cookies.get('token')
    if token:
        return redirect(url_for('dashboard.dashboard_page'))
    return redirect(url_for('auth.login'))

if __name__ == "__main__":
    app.run(debug=True, port=8080)
