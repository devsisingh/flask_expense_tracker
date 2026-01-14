# tests/conftest.py
import pytest
import sys
import os
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from main import create_app, db, Expense

@pytest.fixture
def client():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    }

    app = create_app(test_config)

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Seed test data
            expense = Expense(desc="Test Expense", amount=100, currency="INR")
            db.session.add(expense)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

