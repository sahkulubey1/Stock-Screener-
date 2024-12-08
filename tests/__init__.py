import os
import pytest
from app import app

# Configure Flask test client
os.environ["FLASK_ENV"] = "testing"

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# app.py (or __init__.py)
from flask import Flask
app = Flask(__name__)

# Configure directly in app.py
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
app.secret_key = "test_secret"

# Add any other configurations here

