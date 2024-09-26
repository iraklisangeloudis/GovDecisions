import pytest
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_index(client):
    """Test the index page"""
    response = client.get('/')
    # Check if home route (/) is functioning properly.
    assert response.status_code == 200
    # Check if the word 'Decisions' is in the response
    assert b"Decisions" in response.data

