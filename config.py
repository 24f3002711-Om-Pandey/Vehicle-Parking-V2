from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Flask application configuration
# Ensure app is imported if it's needed for SQLAlchemy directly in config,
# but typically app.config is set directly.
# For simplicity, we'll assume app is passed or configured directly in app.py
# app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///app.db')
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', False)

# Database URI for SQLAlchemy. Defaults to 'sqlite:///app.db' if not set in environment.
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///app.db')

# Disable SQLAlchemy event system for tracking modifications for better performance
SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() in ('true', '1', 't')

# Secret key for session management. Important for security.
SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_should_be_changed')

# Note: In a real application, sensitive information like SECRET_KEY should be
# managed securely (e.g., environment variables, secret management services).
