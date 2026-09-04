#!/bin/bash
set -e

# -----------------------------
# RUTAS PRINCIPALES
# -----------------------------
BASE_DIR="/home/mmestre01/Desktop/portafolios"           # Carpeta padre
GITWEB_DIR="$BASE_DIR/gitweb"                           # Carpeta GitWeb
FRONTEND_DIR="$GITWEB_DIR/gitweb-frontend"              # React frontend
GEMA_GAME_DIR="$BASE_DIR/felices26Gema"                 # Minijuego Felices 26, Gema
BACKEND_DIR="$BASE_DIR"                                 # Flask backend principal con Digame
LANDING_FILE="$BASE_DIR/index.html"                     # Landing principal
LOG_FILE="/home/mmestre01/cloudflared_manual.log"       # Log del túnel

echo "🚀 Iniciando despliegue..."

# -----------------------------
# LIMPIAR PROCESOS ANTERIORES
# -----------------------------
echo "🧹 Matando procesos previos..."

if systemctl list-unit-files digame.service >/dev/null 2>&1; then
    echo "ℹ️  Digame está gestionado por systemd; no se matan procesos manualmente."
else
    # Fallback antiguo: detener solo el Gunicorn de Digame en 5002.
    pkill -f "gunicorn.*127.0.0.1:5002.*app:app" || true
    sleep 2
fi

echo "✅ Procesos previos detenidos."

# -----------------------------
# LANDING PRINCIPAL
# -----------------------------
if [ -f "$LANDING_FILE" ]; then
    echo "🏠 Landing index.html encontrada en $BASE_DIR"
else
    echo "⚠️  Landing index.html NO encontrada en $BASE_DIR. Por favor, crea tu landing antes de continuar."
fi

# -----------------------------
# FRONTEND REACT (/gitweb)
# -----------------------------
echo "📦 Reconstruyendo frontend React..."
cd "$FRONTEND_DIR"

# Forzar permisos al usuario actual
sudo chown -R $USER:$USER build || true

# Borrar build anterior si existe
rm -rf build || true

# Instalar dependencias y reconstruir
npm install
npm run build

# Dar permisos correctos para Nginx
sudo chown -R www-data:www-data build
sudo chmod -R 755 build

echo "✅ Frontend React desplegado en /gitweb"

# -----------------------------
# MINIJUEGO FELICES 26, GEMA
# -----------------------------
if [ -f "$GEMA_GAME_DIR/package.json" ]; then
    echo "🎂 Reconstruyendo minijuego /felices26Gema..."
    cd "$GEMA_GAME_DIR"
    npm install
    npm run build
    sudo chown -R www-data:www-data dist
    sudo chmod -R 755 dist
    echo "✅ Minijuego desplegado en /felices26Gema"
fi

# -----------------------------
# NGINX
# -----------------------------
echo "🔄 Reiniciando Nginx..."
sudo nginx -t
sudo systemctl restart nginx
echo "✅ Nginx reiniciado."

# -----------------------------
# BACKEND FLASK
# -----------------------------
echo "🔄 Iniciando backend Flask con Digame..."
cd "$BACKEND_DIR"
source venv/bin/activate

if systemctl list-unit-files digame.service >/dev/null 2>&1; then
    sudo systemctl restart digame.service
else
    # Fallback para máquinas donde el servicio aún no está instalado.
    gunicorn --bind 127.0.0.1:5002 app:app --workers 3 --daemon
fi

echo "✅ Backend Dígame iniciado en 127.0.0.1:5002"
