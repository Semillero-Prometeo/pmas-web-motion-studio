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
    seeds: dict[tuple[int, int], list[Any]] = {}
    order: list[tuple[int, int]] = []
    for item in blocks:
        pca, servo = int(item[0]), int(item[1])
        key = (pca, servo)
        if key not in seeds:
            seeds[key] = item
            order.append(key)
            continue
        if float(item[2]) < float(seeds[key][2]):
            seeds[key] = item
    return [
        [
            pca,
            servo,
            0,
            2,
            int(seeds[(pca, servo)][4]),
            int(seeds[(pca, servo)][5]),
            str(seeds[(pca, servo)][6]),
        ]
        for pca, servo in order
    ]
