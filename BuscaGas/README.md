# BuscaGas

MVP web para encontrar las gasolineras más baratas durante una ruta por España. Usa precios públicos de MITECO, rutas reales de openrouteservice (HeiGIT), un prefiltro geoespacial métrico y Matrix para medir el desvío real por carretera.

## Arquitectura

- `app/services/miteco.py`: descarga, normalización y caché de precios.
- `app/services/routing.py`: abstracción de routing y proveedor ORS.
- `app/services/optimizer.py`: corredor, Matrix, filtro y orden por precio.
- `app/utils/geo.py`: proyección UTM y prefiltro Shapely.
- `app/main.py`: FastAPI; `templates/` y `static/`: interfaz Leaflet.

## Requisitos e instalación

Requiere Python 3.12+ y una clave de openrouteservice.

```bash
cd BuscaGas
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
```

En Windows, activa con `.venv\Scripts\activate`. Edita `.env` y añade `ORS_API_KEY`. La clave permanece exclusivamente en el backend.

`MAX_MATRIX_CANDIDATES` limita las estaciones más próximas a la ruta que se
evalúan mediante Matrix (200 por defecto) para respetar las cuotas del proveedor.

## Ejecución

```bash
uvicorn app.main:app --reload
```

Abre `http://127.0.0.1:8000`. La app arranca sin clave, pero geocodificar o buscar devuelve un error claro hasta configurarla.

## Calidad

```bash
pytest
ruff check .
```

Los tests no usan Internet: simulan MITECO, ORS y respuestas Matrix parciales.

## Docker

```bash
docker build -t buscagas .
docker run --env-file .env -p 8000:8000 buscagas
```

## Publicación en mmestre.org/BuscaGas

La configuración del repositorio envía `/BuscaGas/` al servicio local en `127.0.0.1:8003`. Para instalar el servicio por primera vez:

```bash
sudo cp systemd/buscagas.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now buscagas
sudo nginx -t && sudo systemctl reload nginx
```

El HTML usa rutas relativas, por lo que funciona tanto en local como bajo `/BuscaGas/`.
