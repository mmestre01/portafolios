Portafolios de Marc Mestre

## BuscaGas

Aplicación FastAPI independiente publicada en `/BuscaGas/`. Compara precios reales de carburantes del Ministerio y calcula mediante openrouteservice el desvío real por carretera. Consulta `BuscaGas/README.md` para instalación, configuración y servicio systemd.

## Digame

Se ha agregado una nueva funcionalidad completa en `/digame` para grabar mensajes de voz y gestionarlos desde un panel admin en `/digame/admin`.

### Pasos rápidos

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Configurar variables de entorno:
   ```bash
   export DIGAME_ENABLED=true
   export DIGAME_ADMIN_KEY=change_me
   export RASPBERRY_TOKEN=change_me
   export DIGAME_MOCK_RASPBERRY=true
   ```
3. Ejecutar la app:
   ```bash
   python app.py
   ```

### Rutas principales

- `/digame` — interfaz de grabación y solicitud de acceso.
- `/digame/admin` — panel administrativo protegido.
- `/api/digame/audio` — subida de audio.
- `/ws/digame` — WebSocket preparado para Raspberry.

### Modo mock

Cuando `DIGAME_MOCK_RASPBERRY=true`, el sistema simula una Raspberry conectada y marca el audio como reproducido automáticamente.

### Cliente Raspberry

La carpeta `raspberry-digame-client` contiene el cliente websocket preparado para conectarse a `/ws/digame`.

## Felices 26, Gema

Se ha agregado un minijuego web independiente en `/felices26Gema/`, construido con Vite, TypeScript y Phaser 3.

### Pasos rápidos

```bash
cd felices26Gema
npm install
npm run dev
npm run build
```

El resultado de producción queda en `felices26Gema/dist/`. La configuración de Nginx incluida sirve esa carpeta desde `/felices26Gema/`, y el `deploy.sh` reconstruye el juego antes de reiniciar Nginx.
