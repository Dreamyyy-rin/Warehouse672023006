import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from common.session_manager import SessionManager

@pytest.fixture
def client():
    """
    Returns a test client for the Flask app.
    
    The TESTING and WTF_CSRF_ENABLED configuration variables are set to True and False respectively.
    The client is a context manager and should be used with a with statement.
    """
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

@pytest.fixture
def session_manager():
    """
    Returns an instance of SessionManager for use in tests.

    This fixture is meant to be used in tests that require a SessionManager instance.
    """
    return SessionManager()

@pytest.fixture
def test_user_token(session_manager):
    """
    Returns a token for a user with the username "testuser" and the role "user"

    This fixture is meant to be used in tests that require a valid user token.
    """
    return session_manager.generate_token("testuser", "user")

@pytest.fixture
def admin_token(session_manager):
    """
    Returns a token for a user with the username "admin" and the role "admin"

    This fixture is meant to be used in tests that require a valid admin token.
    """
    return session_manager.generate_token("admin", "admin")
