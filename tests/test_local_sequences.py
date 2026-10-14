from fastapi.testclient import TestClient
from src import local_sequences
from src.app import app

ORIGIN = {
    "name": "saludo",
    "description": "Saludo con el brazo derecho",
    "arduino_id": 0,
    "blocks": [[0, 0, 0.0, 2, 500, 5, "P0_S0"]],
}


def client_with_store(tmp_path):
    local_sequences.store = local_sequences.LocalSequenceStore(tmp_path)
    return TestClient(app)


def test_empty_local_list(tmp_path):
    response = client_with_store(tmp_path).get("/local/sequences")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["data"] == []


def test_save_and_list_origin_on_disk(tmp_path):
    client = client_with_store(tmp_path)
    saved = client.post(
        "/local/sequences", json={"sequence": ORIGIN, "overwrite": False}
    )
    assert saved.status_code == 200
    body = saved.json()
    assert "id" not in body
    assert body["name"] == "saludo"
    assert body["description"] == "Saludo con el brazo derecho"
    assert body["blocks"][0] == [0, 0, 0.0, 2, 500, 5, "P0_S0"]

    listed = client.get("/local/sequences")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["data"][0]["name"] == "saludo"
    assert payload["data"][0]["description"] == "Saludo con el brazo derecho"
    assert "id" not in payload["data"][0]

    loaded = client.get("/local/sequences/saludo")
    assert loaded.status_code == 200
    assert loaded.json()["blocks"][0][6] == "P0_S0"


def test_duplicate_without_overwrite_is_rejected(tmp_path):
    client = client_with_store(tmp_path)
    client.post("/local/sequences", json={"sequence": ORIGIN, "overwrite": False})
    again = client.post(
        "/local/sequences", json={"sequence": ORIGIN, "overwrite": False}
    )
    assert again.status_code == 409
    assert "ya existe" in again.json()["detail"].lower()


def test_overwrite_replaces_description(tmp_path):
    client = client_with_store(tmp_path)
    client.post("/local/sequences", json={"sequence": ORIGIN, "overwrite": False})
    updated = dict(ORIGIN)
    updated["description"] = "Otra frase"
    saved = client.post(
        "/local/sequences", json={"sequence": updated, "overwrite": True}
    )
    assert saved.status_code == 200
    assert saved.json()["description"] == "Otra frase"


def test_rejects_path_escape(tmp_path):
    client = client_with_store(tmp_path)
    evil = dict(ORIGIN)
    evil["name"] = "../fuera"
    response = client.post(
        "/local/sequences", json={"sequence": evil, "overwrite": False}
    )
    assert response.status_code == 400


def test_index_has_library_panel():
    text = TestClient(app).get("/").text
    assert 'id="library"' in text
    assert "Secuencias" in text
