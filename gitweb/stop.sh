#!/bin/bash
set -e

echo "🛑 Deteniendo backend y nginx..."

# Parar gunicorn (si está corriendo)
pkill -f "gunicorn.*main:app" || true
echo "✅ Backend detenido."

# Reiniciar nginx para limpiar procesos
sudo systemctl stop nginx
echo "✅ Nginx detenido."

echo "✔️ Todo apagado."
