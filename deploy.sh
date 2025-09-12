#!/bin/bash
set -e

# -----------------------------
# RUTAS PRINCIPALES
# -----------------------------
BASE_DIR="/home/mmestre01/Desktop/portafolis"            # Carpeta padre
GITWEB_DIR="$BASE_DIR/gitweb"                            # Carpeta GitWeb
FRONTEND_DIR="$GITWEB_DIR/gitweb-frontend"              # React frontend
BACKEND_DIR="$GITWEB_DIR"                               # Flask backend
LANDING_FILE="$BASE_DIR/index.html"                     # Landing principal

echo "🚀 Iniciando despliegue..."

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
echo "📦 Construyendo frontend React..."
cd "$FRONTEND_DIR"
npm install          # Asegurarnos de tener dependencias
sudo rm -rf build
npm run build
sudo chown -R www-data:www-data build
sudo chmod -R 755 build
echo "✅ Frontend React desplegado en /gitweb"

# -----------------------------
# NGINX
# -----------------------------
echo "🔄 Reiniciando nginx..."
sudo nginx -t
sudo systemctl restart nginx
echo "✅ Nginx reiniciado."

# -----------------------------
# BACKEND FLASK
# -----------------------------
echo "🔄 Iniciando backend..."
cd "$BACKEND_DIR"
source venv/bin/activate

# Matamos cualquier Gunicorn anterior
pkill -f "gunicorn.*main:app" || true

# Levantamos Gunicorn en background
gunicorn --bind 127.0.0.1:5000 main:app --workers 3 --daemon
echo "✅ Backend iniciado con Gunicorn."

# -----------------------------
# CLOUD FLARE TUNNEL
# -----------------------------
echo "🌐 Levantando Cloudflare Tunnel..."
sudo cloudflared tunnel --config /etc/cloudflared/config.yml run raspi &

# -----------------------------
# FIN DEL DESPLIEGUE
# -----------------------------
IP=$(hostname -I | awk '{print $1}')
echo "🎉 Despliegue completado."
echo "🌐 Landing: http://$IP"
echo "🌐 Proyecto GitWeb: http://$IP/gitweb"
echo "🌐 No olvides que Cloudflare Tunnel debe estar activo: cloudflared tunnel run raspi"
