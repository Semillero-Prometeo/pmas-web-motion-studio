from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.neutro import CATEGORIES


def default_data_dir() -> Path:
    env = os.getenv("MOTION_STUDIO_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "sequences"


class LocalSequenceStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def list_payload(self) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for file_path in sorted(self.data_dir.rglob("*.json")):
            try:
                sequence = self._read_origin(file_path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            rows.append(
                {
                    "name": sequence["name"],
                    "description": sequence["description"],
                    "file_name": file_path.relative_to(self.data_dir).as_posix(),
                }
            )
        return {"total": len(rows), "data": rows}

    def get(self, name: str) -> dict[str, Any]:
        path = self._resolve(name)
        if not path.exists():
            raise FileNotFoundError(f"Secuencia '{name}' no encontrada")
        return self._read_origin(path)

    def save(self, payload: dict[str, Any], overwrite: bool = False) -> dict[str, Any]:
        sequence = self._normalize(payload)
        path = self._resolve(sequence["name"])
        if path.exists() and not overwrite:
            raise FileExistsError(
                f"La secuencia '{sequence['name']}' ya existe. Use overwrite=true para reemplazar."
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(sequence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return sequence

    def _read_origin(self, path: Path) -> dict[str, Any]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            name = path.relative_to(self.data_dir).with_suffix("").as_posix()
            return self._normalize({"name": name, "description": "", "blocks": raw})
        if not isinstance(raw, dict):
            raise ValueError("Formato de secuencia inválido")
        if "name" not in raw or not str(raw.get("name") or "").strip():
            raw = dict(raw)
            raw["name"] = path.relative_to(self.data_dir).with_suffix("").as_posix()
        return self._normalize(raw)

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name or len(name) > 80:
            raise ValueError("Nombre de secuencia inválido")
        description = (
            str(payload.get("description") or "").replace("\n", " ").strip()[:280]
        )
        arduino_id = int(payload.get("arduino_id") or 0)
        category = payload.get("category")
        if category not in CATEGORIES:
            raise ValueError("Categoría inválida")
        tuples = self._tuples(payload.get("blocks"))
        try:
            neutro = self._tuples(payload.get("blocks_neutro"))
        except ValueError as exc:
            raise ValueError("Falta la pista neutra") from exc
        return {
            "name": name,
            "description": description,
            "category": category,
            "arduino_id": arduino_id,
            "blocks": tuples,
            "blocks_neutro": neutro,
        }

    def _tuples(self, raw: object) -> list[list[Any]]:
        if not isinstance(raw, list) or not raw:
            raise ValueError("Define nombre y bloques")
        tuples: list[list[Any]] = []
        for item in raw:
            if isinstance(item, list) and len(item) == 7:
                tuples.append(
                    [
                        int(item[0]),
                        int(item[1]),
                        float(item[2]),
                        float(item[3]),
                        int(item[4]),
                        int(item[5]),
                        str(item[6]),
                    ]
                )
                continue
            if isinstance(item, dict):
                tuples.append(
                    [
                        int(item.get("pca") or 0),
                        int(item.get("servo") or 0),
                        float(item.get("inicio") or 0),
                        float(item.get("dur") or 1),
                        int(item.get("pos") or 0),
                        int(item.get("vel") or 1),
                        str(item.get("nombre") or ""),
                    ]
                )
                continue
            raise ValueError("Formato de secuencia inválido")
        return tuples

    def _resolve(self, name: str) -> Path:
        normalized = name.replace("\\", "/").strip("/")
        if not normalized:
            raise ValueError("Nombre de secuencia inválido")
        parts: list[str] = []
        for part in normalized.split("/"):
            stripped = part.strip()
            if not stripped or stripped in {".", ".."}:
                raise ValueError("Nombre de secuencia inválido")
            parts.append(stripped)
        relative = Path(*parts).with_suffix(".json")
        path = (self.data_dir / relative).resolve()
        data_root = self.data_dir.resolve()
        if path != data_root and data_root not in path.parents:
            raise ValueError("Nombre de secuencia inválido")
        return path


store = LocalSequenceStore()
