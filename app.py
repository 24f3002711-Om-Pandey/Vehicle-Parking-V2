from flask import Flask, render_template, request, url_for, redirect, session
from flask_sqlalchemy import SQLAlchemy
import os
from db import init_db, shutdown_session, db_session
import config # Import config to load environment variables and app configurations
from models import User

# Initialize Flask application
app = Flask(__name__)
app.debug = True # Enable debug mode for development

# Load configuration from config.py
app.config.from_object('config')

def create_admin():
    admin_username = "admin"
    admin_email = "admin@parkit.com"
    admin_password = "admin123"  # In production, hash and use env vars!
    admin = db_session.query(User).filter_by(Username=admin_username).first()
    if not admin:
        admin = User(
            Username=admin_username,
            Name="Administrator",
            Email=admin_email,
            is_admin=True
        )
        admin.set_password(admin_password)
        db_session.add(admin)
        db_session.commit()
        print("Admin user created.")

# Initialize the database
init_db()
create_admin()

# Register a teardown function to remove the database session after each request
@app.teardown_appcontext
def remove_session(exception=None):
    shutdown_session(exception)

# Import routes after app initialization to avoid circular imports
from routes import bp
app.register_blueprint(bp)

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = db_session.query(User).get(session['user_id'])
    return dict(current_user=user)

if __name__ == '__main__':
    # Run the Flask application
    app.run(debug=True)