from pathlib import Path

CSS = Path("src/static/editor.css").read_text(encoding="utf-8")


def test_canvas_is_cool_paper_not_industrial_night():
    assert "--bg: #eef2f6" in CSS
    assert "#000f1d" not in CSS
    assert "#10b981" not in CSS
    assert "#ffffff" not in CSS


def test_chrome_is_navy_and_neutro_is_reserved_emerald():
    assert "#0B2540" in CSS
    assert "#059669" in CSS
    assert "#38bdf8" in CSS
    assert "#dc2626" in CSS
