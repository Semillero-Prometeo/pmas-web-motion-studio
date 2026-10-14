import pytest
from src.neutro import generate_neutro


def test_first_pos_per_servo():
    blocks = [
        [0, 0, 1.0, 2, 900, 4, "tarde"],
        [0, 0, 0.0, 2, 100, 5, "temprano"],
        [0, 1, 0.5, 1, 300, 2, "otro"],
    ]
    assert generate_neutro(blocks) == [
        [0, 0, 0, 2, 100, 5, "temprano"],
        [0, 1, 0, 2, 300, 2, "otro"],
    ]


def test_tie_keeps_first_in_array():
    blocks = [
        [0, 0, 0.0, 2, 10, 1, "a"],
        [0, 0, 0.0, 2, 99, 9, "b"],
    ]
    assert generate_neutro(blocks) == [[0, 0, 0, 2, 10, 1, "a"]]


def test_replace_flag_required_when_existing():
    existing = [[0, 0, 0, 2, 1, 1, "x"]]
    with pytest.raises(ValueError, match="ya existe"):
        generate_neutro([[0, 0, 0, 2, 2, 2, "y"]], existing=existing, replace=False)
    assert generate_neutro([[0, 0, 0, 2, 2, 2, "y"]], existing=existing, replace=True) == [
        [0, 0, 0, 2, 2, 2, "y"]
    ]
