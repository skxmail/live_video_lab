#!/bin/bash
set -e

echo "=== Sistema de Monitoreo de Calidad de Streaming ==="
echo ""

# Crear directorios necesarios
mkdir -p logs
mkdir -p media/www

echo "1. Construyendo imagen de monitoreo..."
docker build -f Dockerfile.monitor -t streaming-monitor .

echo ""
echo "2. Iniciando servicios..."
docker compose up -d

echo ""
echo "3. Esperando a que los servicios estén listos..."
sleep 10

echo ""
echo "4. Verificando estado de los servicios..."

# Verificar que el packager esté funcionando
if docker compose ps packager | grep -q "Up"; then
    echo "✓ Packager está funcionando"
else
    echo "✗ Error: Packager no está funcionando"
    exit 1
fi

# Verificar que el player esté funcionando
if docker compose ps player | grep -q "Up"; then
    echo "✓ Player está funcionando"
else
    echo "✗ Error: Player no está funcionando"
    exit 1
fi

# Verificar que el monitor esté funcionando
if docker compose ps monitor | grep -q "Up"; then
    echo "✓ Monitor está funcionando"
else
    echo "✗ Error: Monitor no está funcionando"
    exit 1
fi

echo ""
echo "=== URLs de Acceso ==="
echo "Player: http://localhost:8080"
echo "Monitor Dashboard: http://localhost:8081"
echo "Quality Monitor: http://localhost:8080/quality_monitor.html"
echo ""

echo "=== Comandos Útiles ==="
echo "Ver logs del monitor: docker compose logs -f monitor"
echo "Analizar calidad: docker exec monitor ./quality_analyzer.sh /media/www/h264_360p_1.m4s /app/logs"
echo "Ver métricas: cat logs/stream_quality.json | jq '.[-1]'"
echo ""

echo "=== Monitoreo en Tiempo Real ==="
echo "El sistema está monitoreando automáticamente:"
echo "- Disponibilidad del manifest"
echo "- Bitrates disponibles"
echo "- Resoluciones"
echo "- Estado de la red"
echo "- Errores de streaming"
echo ""

echo "Los datos se guardan en:"
echo "- logs/stream_quality.json (métricas del stream)"
echo "- logs/ (archivos de análisis de calidad)"
echo ""

echo "Para detener el sistema: docker compose down"
echo "Para ver logs en tiempo real: docker compose logs -f" 