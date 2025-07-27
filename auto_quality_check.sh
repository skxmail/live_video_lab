#!/bin/bash
set -e

# Script para análisis automático de calidad de segmentos
# Se ejecuta periódicamente para analizar los segmentos generados

LOG_DIR="./logs/quality_analysis"
SEGMENT_DIR="./media/www"
MONITOR_CONTAINER="monitor"

# Crear directorio de logs
mkdir -p "$LOG_DIR"

echo "=== Análisis Automático de Calidad de Segmentos ==="
echo "Directorio de segmentos: $SEGMENT_DIR"
echo "Directorio de logs: $LOG_DIR"
echo ""

# Función para analizar un segmento
analyze_segment() {
    local segment_file="$1"
    local output_dir="$2"
    
    echo "Analizando: $(basename "$segment_file")"
    
    # Ejecutar análisis usando el contenedor monitor
    docker exec "$MONITOR_CONTAINER" /app/quality_analyzer.sh \
        "$segment_file" \
        "$output_dir" 2>/dev/null || echo "Error analizando $segment_file"
}

# Función para generar reporte resumido
generate_summary_report() {
    local report_file="$LOG_DIR/summary_report_$(date +%Y%m%d_%H%M%S).txt"
    
    echo "=== REPORTE RESUMIDO DE CALIDAD ===" > "$report_file"
    echo "Fecha: $(date)" >> "$report_file"
    echo "Total de segmentos analizados: $(find "$LOG_DIR" -name "quality_report.txt" | wc -l)" >> "$report_file"
    echo "" >> "$report_file"
    
    # Buscar todos los reportes de calidad
    find "$LOG_DIR" -name "quality_report.txt" | while read -r report; do
        echo "--- $(basename "$(dirname "$report")") ---" >> "$report_file"
        cat "$report" >> "$report_file"
        echo "" >> "$report_file"
    done
    
    echo "Reporte resumido guardado en: $report_file"
}

# Función para detectar problemas
detect_issues() {
    local issues_file="$LOG_DIR/issues_$(date +%Y%m%d_%H%M%S).txt"
    
    echo "=== DETECCIÓN DE PROBLEMAS ===" > "$issues_file"
    echo "Fecha: $(date)" >> "$issues_file"
    echo "" >> "$issues_file"
    
    # Buscar problemas en los logs
    find "$LOG_DIR" -name "*.log" | while read -r log_file; do
        echo "--- $(basename "$log_file") ---" >> "$issues_file"
        
        # Buscar errores específicos
        if grep -q "error\|Error\|ERROR" "$log_file" 2>/dev/null; then
            grep -i "error" "$log_file" >> "$issues_file"
        fi
        
        # Buscar warnings
        if grep -q "warning\|Warning\|WARNING" "$log_file" 2>/dev/null; then
            grep -i "warning" "$log_file" >> "$issues_file"
        fi
        
        # Buscar problemas de calidad específicos
        if grep -q "black\|artifact\|macroblock" "$log_file" 2>/dev/null; then
            grep -i "black\|artifact\|macroblock" "$log_file" >> "$issues_file"
        fi
        
        echo "" >> "$issues_file"
    done
    
    echo "Reporte de problemas guardado en: $issues_file"
}

# Función principal de análisis
main_analysis() {
    echo "Iniciando análisis automático..."
    
    # Buscar segmentos de video
    local video_segments=($(find "$SEGMENT_DIR" -name "h264_*.m4s" -type f))
    local audio_segments=($(find "$SEGMENT_DIR" -name "audio_*.m4s" -type f))
    
    echo "Encontrados ${#video_segments[@]} segmentos de video"
    echo "Encontrados ${#audio_segments[@]} segmentos de audio"
    echo ""
    
    # Analizar segmentos de video (últimos 5 para no sobrecargar)
    local count=0
    for segment in "${video_segments[@]: -5}"; do
        if [ -f "$segment" ]; then
            local segment_name=$(basename "$segment" .m4s)
            local output_dir="$LOG_DIR/$segment_name"
            
            analyze_segment "$segment" "$output_dir"
            ((count++))
        fi
    done
    
    # Analizar segmentos de audio (últimos 3)
    for segment in "${audio_segments[@]: -3}"; do
        if [ -f "$segment" ]; then
            local segment_name=$(basename "$segment" .m4s)
            local output_dir="$LOG_DIR/$segment_name"
            
            analyze_segment "$segment" "$output_dir"
            ((count++))
        fi
    done
    
    echo ""
    echo "Análisis completado. $count segmentos procesados."
    
    # Generar reportes
    generate_summary_report
    detect_issues
    
    echo ""
    echo "=== RESUMEN ==="
    echo "Logs guardados en: $LOG_DIR"
    echo "Último reporte: $(ls -t "$LOG_DIR"/summary_report_*.txt 2>/dev/null | head -1 || echo 'N/A')"
    echo "Últimos problemas: $(ls -t "$LOG_DIR"/issues_*.txt 2>/dev/null | head -1 || echo 'N/A')"
}

# Función para monitoreo continuo
continuous_monitoring() {
    local interval="${1:-300}"  # 5 minutos por defecto
    
    echo "Iniciando monitoreo continuo cada $interval segundos..."
    echo "Presiona Ctrl+C para detener"
    echo ""
    
    while true; do
        main_analysis
        echo "Esperando $interval segundos hasta el próximo análisis..."
        sleep "$interval"
    done
}

# Función para limpiar logs antiguos
cleanup_old_logs() {
    local days="${1:-7}"  # Mantener logs de 7 días por defecto
    
    echo "Limpiando logs más antiguos de $days días..."
    
    find "$LOG_DIR" -type f -mtime +$days -delete 2>/dev/null || true
    find "$LOG_DIR" -type d -empty -delete 2>/dev/null || true
    
    echo "Limpieza completada."
}

# Procesar argumentos
case "${1:-}" in
    "continuous"|"cont")
        continuous_monitoring "${2:-300}"
        ;;
    "cleanup"|"clean")
        cleanup_old_logs "${2:-7}"
        ;;
    "once"|"single")
        main_analysis
        ;;
    "help"|"-h"|"--help")
        echo "Uso: $0 [comando] [parámetros]"
        echo ""
        echo "Comandos:"
        echo "  once, single    - Análisis único (por defecto)"
        echo "  continuous, cont [intervalo] - Monitoreo continuo (intervalo en segundos, default: 300)"
        echo "  cleanup, clean [días] - Limpiar logs antiguos (días, default: 7)"
        echo "  help, -h, --help - Mostrar esta ayuda"
        echo ""
        echo "Ejemplos:"
        echo "  $0                    # Análisis único"
        echo "  $0 continuous 60      # Monitoreo cada minuto"
        echo "  $0 cleanup 3          # Limpiar logs de más de 3 días"
        ;;
    *)
        main_analysis
        ;;
esac 