import json
from app import application


def test_home():
    client = application.test_client()
    response = client.get("/")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "running"


def test_health():
    client = application.test_client()
    response = client.get("/health")
    assert response.status_code == 200
