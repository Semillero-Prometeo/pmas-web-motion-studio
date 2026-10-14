# R-ONE Motion Studio

Editor web de secuencias para el androide R-ONE (Prometeo, Universidad Libre, Bogotá). Se crea un movimiento en una línea de tiempo (bloques por servo, regla en segundos, cabezal de reproducción) y se guarda como JSON de origen: `name`, `description` y bloques en 7-tuplas `[pca, servo, inicio, dur, pos, vel, nombre]`. El estudio **no** asigna `id`; eso lo hace robótica cuando está acoplado.

## Dos modos

| Modo | Cuándo | Dónde viven las secuencias | Reproducir |
|---|---|---|---|
| **Suelto** | Arranque local, sin gateway ni sesión | `data/sequences/` en este repositorio | Solo la línea de tiempo (cabezal). No habla con el Arduino. |
| **Acoplado** | Compose + iframe en `pmas-web-main` `/sequences`, con JWT y rol activo | Robótica (`POST /sequence/file`) | Play envía los bloques a `POST /sequence/play` |

En suelto, la columna derecha lista lo guardado en disco. En acoplado, lista las secuencias de robótica: clic para editar, Play para previsualizar.

## Arranque suelto en Windows

1. Instala [Python 3.11 o superior](https://www.python.org/downloads/) y marca **Add python.exe to PATH**.
2. Doble clic en `start-studio.bat` (o ejecútalo desde `cmd`).
3. Abre [http://127.0.0.1:4210](http://127.0.0.1:4210).

El script crea `.venv`, instala este paquete y levanta Uvicorn en el puerto **4210**. Los JSON quedan en `data\sequences`.

Para parar: Ctrl+C en la ventana de la consola.

## Arranque suelto en Linux o macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
mkdir -p data/sequences
uvicorn src.app:app --host 127.0.0.1 --port 4210 --reload --reload-dir src
```

Variable opcional: `MOTION_STUDIO_DATA_DIR` apunta a otra carpeta de JSON.

## Arranque acoplado (lanzador R-ONE)

Desde la raíz de `pba-launcher`:

```bash
sudo docker compose up
```

El servicio `pmas-web-motion-studio` queda en el puerto `MOTION_STUDIO_PORT` (4210). La interfaz Angular lo incrusta en `/sequences` y le envía el JWT y el rol activo por `postMessage`. Guardar y listar pasan por el gateway hacia robótica.

## JSON de origen

```json
{
  "name": "saludo",
  "description": "Saludo con el brazo derecho",
  "arduino_id": 0,
  "blocks": [[0, 0, 0.0, 2, 500, 5, "P0_S0"]]
}
```

- `name`: 1–80 caracteres.
- `description`: 0–280, una línea, para el prompt del turno.
- El estudio no escribe `id` ni `version`.

## Pruebas

```bash
python -m pytest -q
```

## Layout

```
src/app.py                 FastAPI: editor estático y disco local
src/local_sequences.py     Listar / leer / guardar JSON de origen
src/static/                Línea de tiempo (HTML, CSS, JS)
data/sequences/            Almacén suelto
start-studio.bat           Arranque suelto en Windows
Dockerfile.dev             Imagen para Compose
```
