#!/bin/bash
set -e

# -----------------------------
# RUTAS PRINCIPALES
# -----------------------------
BASE_DIR="/home/mmestre01/Desktop/portafolios"           # Carpeta padre
GITWEB_DIR="$BASE_DIR/gitweb"                           # Carpeta GitWeb
FRONTEND_DIR="$GITWEB_DIR/gitweb-frontend"              # React frontend
BACKEND_DIR="$GITWEB_DIR"                               # Flask backend
LANDING_FILE="$BASE_DIR/index.html"                     # Landing principal
LOG_FILE="/home/mmestre01/cloudflared_manual.log"       # Log del túnel

echo "🚀 Iniciando despliegue limpio..."

# -----------------------------
# LIMPIAR PROCESOS ANTERIORES
# -----------------------------
echo "🧹 Matando procesos previos..."

# Gunicorn
pkill -f "gunicorn.*main:app" || true

# Cloudflared
pkill -f "cloudflared.*tunnel" || true

# Espera un poco para evitar conflictos
sleep 2

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
# NGINX
# -----------------------------
echo "🔄 Reiniciando Nginx..."
sudo nginx -t
sudo systemctl restart nginx
echo "✅ Nginx reiniciado."

# -----------------------------
# BACKEND FLASK
# -----------------------------
echo "🔄 Iniciando backend Flask..."
cd "$BACKEND_DIR"
source venv/bin/activate

# Levantar Gunicorn en primer plano (logs visibles en consola)
echo "📜 Mostrando logs de Gunicorn a continuación..."
exec gunicorn --bind 127.0.0.1:5000 main:app --workers 3 --reload
