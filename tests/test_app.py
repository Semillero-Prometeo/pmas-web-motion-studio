from fastapi.testclient import TestClient

from src.app import app


def test_index_serves_editor():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    text = response.text.lower()
    assert "description" in text or "descripcion" in text or "descripción" in text
    assert "nombre" in text
