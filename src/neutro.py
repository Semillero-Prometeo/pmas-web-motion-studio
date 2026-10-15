from typing import Any

CATEGORIES = (
    "cara",
    "cuello",
    "brazo_derecho",
    "brazo_izquierdo",
    "torso",
    "cadera",
)


def generate_neutro(
    blocks: list[list[Any]],
    existing: list[list[Any]] | None = None,
    replace: bool = False,
) -> list[list[Any]]:
    if existing and not replace:
        raise ValueError("La pista neutra ya existe")
    if not blocks:
        return []
    ordered = sorted(enumerate(blocks), key=lambda pair: (float(pair[1][2]), pair[0]))
    prev: dict[tuple[int, int], int] = {}
    undos: list[tuple[int, list[Any]]] = []
    for index, item in ordered:
        pca, servo = int(item[0]), int(item[1])
        key = (pca, servo)
        inicio = float(item[2])
        dur = float(item[3])
        pos = int(item[4])
        vel = int(item[5])
        nombre = str(item[6])
        undos.append(
            (index, [pca, servo, inicio, dur, prev.get(key, 0), vel, nombre])
        )
        prev[key] = pos
    t_end = max(float(item[2]) + float(item[3]) for item in blocks)
    out: list[tuple[float, int, list[Any]]] = []
    for index, row in undos:
        inicio = float(row[2])
        dur = float(row[3])
        row[2] = t_end - (inicio + dur)
        out.append((float(row[2]), -index, row))
    out.sort(key=lambda item: (item[0], item[1]))
    return [
        [row[0], row[1], row[2], row[3], row[4], row[5], row[6]]
        for _, _, row in out
    ]
