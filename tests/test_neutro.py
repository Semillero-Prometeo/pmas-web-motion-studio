import pytest
from src.neutro import generate_neutro


def test_same_servo_two_steps_rewinds_to_rest():
    blocks = [
        [0, 0, 0.0, 1, 200, 5, "a"],
        [0, 0, 1.0, 0.5, 400, 5, "b"],
    ]
    assert generate_neutro(blocks) == [
        [0, 0, 0.0, 0.5, 200, 5, "b"],
        [0, 0, 0.5, 1, 0, 5, "a"],
    ]


def test_two_servos_each_return_to_zero():
    blocks = [
        [0, 0, 0.0, 1, 200, 5, "a"],
        [0, 1, 0.0, 1, 300, 4, "b"],
    ]
    assert generate_neutro(blocks) == [
        [0, 1, 0.0, 1, 0, 4, "b"],
        [0, 0, 0.0, 1, 0, 5, "a"],
    ]


def test_inicio_tie_uses_array_index_then_inverts():
    blocks = [
        [0, 0, 0.0, 1, 10, 1, "a"],
        [0, 0, 0.0, 1, 99, 9, "b"],
    ]
    assert generate_neutro(blocks) == [
        [0, 0, 0.0, 1, 10, 9, "b"],
        [0, 0, 0.0, 1, 0, 1, "a"],
    ]


def test_gap_is_mirrored():
    blocks = [
        [0, 0, 0.0, 1, 200, 5, "a"],
        [0, 0, 2.0, 1, 400, 5, "b"],
    ]
    assert generate_neutro(blocks) == [
        [0, 0, 0.0, 1, 200, 5, "b"],
        [0, 0, 2.0, 1, 0, 5, "a"],
    ]


def test_replace_flag_required_when_existing():
    existing = [[0, 0, 0, 2, 1, 1, "x"]]
    with pytest.raises(ValueError, match="ya existe"):
        generate_neutro([[0, 0, 0, 1, 2, 2, "y"]], existing=existing, replace=False)
    assert generate_neutro(
        [[0, 0, 0, 1, 2, 2, "y"]], existing=existing, replace=True
    ) == [[0, 0, 0.0, 1, 0, 2, "y"]]
