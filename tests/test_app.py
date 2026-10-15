from fastapi.testclient import TestClient
from src.app import app


def test_index_has_category_and_neutro_controls():
    text = TestClient(app).get("/").text
    chrome = text.split('<header class="chrome">', 1)[1].split("</header>", 1)[0]
    assert 'id="name"' not in chrome
    assert 'id="description"' not in chrome
    assert 'id="category"' not in chrome
    assert 'id="arduino_id"' not in chrome
    assert 'id="save-dialog"' in text
    dialog = text.split('id="save-dialog"', 1)[1]
    assert 'id="name"' in dialog
    assert 'id="description"' in dialog
    assert 'minlength="10"' in dialog
    assert 'id="category"' in dialog
    assert 'id="arduino_id"' in dialog
    assert 'id="track-gesto"' in text
    assert 'id="track-neutro"' in text
    assert 'id="generate-neutro"' in text
    assert "brazo_derecho" in text


def test_toolbar_order_is_play_stop_add_tracks_save():
    text = TestClient(app).get("/").text
    actions = text.split('<div class="actions">', 1)[1].split("</div>", 1)[0]
    ids = []
    for token in (
        'id="play"',
        'id="stop"',
        'id="add"',
        'id="track-gesto"',
        'id="track-neutro"',
        'id="generate-neutro"',
        'id="save"',
        'id="load"',
    ):
        ids.append((actions.index(token), token))
    assert [item[1] for item in ids] == [item[1] for item in sorted(ids)]


def test_index_serves_editor():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    text = response.text.lower()
    assert "description" in text or "descripcion" in text or "descripción" in text
    assert "nombre" in text
    assert 'id="tracks"' in response.text
    assert "agregar" in text
    assert "material-symbols-outlined" in text
    assert "space grotesk" in text
