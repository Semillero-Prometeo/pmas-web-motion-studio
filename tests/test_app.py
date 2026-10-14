from fastapi.testclient import TestClient
from src.app import app


def test_index_has_category_and_neutro_controls():
    text = TestClient(app).get("/").text
    assert 'id="category"' in text
    assert 'id="track-gesto"' in text
    assert 'id="track-neutro"' in text
    assert 'id="generate-neutro"' in text
    assert "brazo_derecho" in text


def test_index_serves_editor():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    text = response.text.lower()
    assert "description" in text or "descripcion" in text or "descripción" in text
    assert "nombre" in text
    assert 'id="tracks"' in response.text
    assert "agregar" in text
