#!/bin/bash
set -e

BASE_DIR="/home/mmestre01/Desktop/portafolis/gitweb"
FRONTEND_DIR="$BASE_DIR/gitweb-frontend"
BACKEND_DIR="$BASE_DIR"

echo "🚀 Iniciando despliegue..."

# --- FRONTEND ---
echo "📦 Construyendo frontend..."
cd "$FRONTEND_DIR"
npm install          # asegurarnos de tener dependencias
sudo rm -rf build
npm run build
sudo chown -R www-data:www-data build
sudo chmod -R 755 build
echo "✅ Frontend desplegado."

# --- NGINX ---
echo "🔄 Reiniciando nginx..."
sudo systemctl restart nginx
echo "✅ Nginx reiniciado."

# --- BACKEND ---
echo "🔄 Iniciando backend..."
cd "$BACKEND_DIR"
source venv/bin/activate

# Matamos cualquier Gunicorn anterior
pkill -f "gunicorn.*main:app" || true

# Levantamos Gunicorn en background para que no bloquee
gunicorn --bind 127.0.0.1:5000 main:app --workers 3 --daemon
echo "✅ Backend iniciado con Gunicorn."

# Mostrar URL local y recordatorio del túnel
IP=$(hostname -I | awk '{print $1}')
echo "🎉 Despliegue completado. Accede en local: http://$IP"
echo "🌐 No olvides levantar tu Cloudflare Tunnel:"
echo "   cloudflared tunnel run raspi"
sudo cloudflared tunnel --config /etc/cloudflared/config.yml run raspi

