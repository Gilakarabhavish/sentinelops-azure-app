from app import application


def test_home():
    client = application.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"SentinelOps Lite" in response.data


def test_health():
    client = application.test_client()

    response = client.get("/health")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "healthy"