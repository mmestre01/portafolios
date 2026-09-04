# Raspberry Digame Client

Este cliente se conecta a la ruta WebSocket `/ws/digame` del servidor y reproduce los mensajes de voz enviados desde la aplicación web.

## Requisitos

- Python 3.8+
- `pip install -r requirements.txt`
- La variable `SERVER_URL` debe apuntar al servidor donde se ejecuta la aplicación Digame.
- `RASPBERRY_TOKEN` debe coincidir con la variable de entorno del servidor.

## Configuración

Crea un archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
```

## Ejecución

```bash
export SERVER_URL=http://localhost:5000
export RASPBERRY_TOKEN=change_me
python client.py
```

## Comportamiento

- Se reconecta automáticamente si la conexión se pierde.
- Descarga el audio desde la URL recibida.
- Reproduce el audio con `ffplay` o `aplay` si están disponibles.
- Envía eventos `played` o `error` al servidor.
