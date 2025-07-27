#!/bin/bash
set -e

# Script para analizar calidad de video usando FFmpeg
# Uso: ./quality_analyzer.sh <input_file> [output_dir]

INPUT_FILE="$1"
OUTPUT_DIR="${2:-./quality_analysis}"

if [ -z "$INPUT_FILE" ]; then
    echo "Uso: $0 <input_file> [output_dir]"
    echo "Ejemplo: $0 ./media/www/h264_360p_1.m4s ./quality_logs"
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: El archivo $INPUT_FILE no existe"
    exit 1
fi

# Crear directorio de salida
mkdir -p "$OUTPUT_DIR"

echo "=== Análisis de Calidad de Video ==="
echo "Archivo: $INPUT_FILE"
echo "Directorio de salida: $OUTPUT_DIR"
echo ""

# 1. Información básica del archivo
echo "1. Información básica del archivo..."
ffprobe -v quiet -print_format json -show_format -show_streams "$INPUT_FILE" > "$OUTPUT_DIR/file_info.json"
echo "✓ Información guardada en $OUTPUT_DIR/file_info.json"

# 2. Análisis de PSNR (si hay archivo de referencia)
if [ -f "reference.mp4" ]; then
    echo "2. Análisis PSNR con archivo de referencia..."
    ffmpeg -i "$INPUT_FILE" -i reference.mp4 -lavfi psnr=stats_file="$OUTPUT_DIR/psnr.log" -f null - 2>/dev/null
    echo "✓ PSNR guardado en $OUTPUT_DIR/psnr.log"
else
    echo "2. PSNR: No hay archivo de referencia (reference.mp4)"
fi

# 3. Análisis SSIM (Structural Similarity Index)
echo "3. Análisis SSIM..."
ffmpeg -i "$INPUT_FILE" -vf ssim=stats_file="$OUTPUT_DIR/ssim.log" -f null - 2>/dev/null
echo "✓ SSIM guardado en $OUTPUT_DIR/ssim.log"

# 4. Análisis de métricas de codificación
echo "4. Métricas de codificación..."
ffmpeg -i "$INPUT_FILE" -vf "signalstats=stats=1:out=1" -f null - 2> "$OUTPUT_DIR/signalstats.log"
echo "✓ Métricas de señal guardadas en $OUTPUT_DIR/signalstats.log"

# 5. Análisis de audio
echo "5. Análisis de audio..."
ffmpeg -i "$INPUT_FILE" -af "volumedetect" -f null - 2> "$OUTPUT_DIR/audio_analysis.log"
echo "✓ Análisis de audio guardado en $OUTPUT_DIR/audio_analysis.log"

# 6. Detección de macroblocking y artifacts
echo "6. Detección de artifacts..."
ffmpeg -i "$INPUT_FILE" -vf "blackdetect=d=0.1:pix_th=0.1,blackframe=amount=98:threshold=32" -f null - 2> "$OUTPUT_DIR/artifact_detection.log"
echo "✓ Detección de artifacts guardada en $OUTPUT_DIR/artifact_detection.log"

# 7. Análisis de frames
echo "7. Análisis de frames..."
ffmpeg -i "$INPUT_FILE" -vf "fps=fps=1/1" -f null - 2> "$OUTPUT_DIR/frame_analysis.log"
echo "✓ Análisis de frames guardado en $OUTPUT_DIR/frame_analysis.log"

# 8. Generar reporte resumido
echo "8. Generando reporte resumido..."
{
    echo "=== REPORTE DE CALIDAD DE VIDEO ==="
    echo "Fecha: $(date)"
    echo "Archivo: $INPUT_FILE"
    echo ""
    
    echo "--- INFORMACIÓN BÁSICA ---"
    if command -v jq &> /dev/null; then
        jq -r '.format.duration // "N/A"' "$OUTPUT_DIR/file_info.json" | xargs -I {} echo "Duración: {} segundos"
        jq -r '.streams[] | select(.codec_type=="video") | "Resolución: \(.width)x\(.height)"' "$OUTPUT_DIR/file_info.json" | head -1
        jq -r '.streams[] | select(.codec_type=="video") | "Codec: \(.codec_name)"' "$OUTPUT_DIR/file_info.json" | head -1
        jq -r '.streams[] | select(.codec_type=="video") | "Bitrate: \(.bit_rate // "N/A")"' "$OUTPUT_DIR/file_info.json" | head -1
    else
        echo "Instala 'jq' para ver información detallada"
    fi
    
    echo ""
    echo "--- ANÁLISIS DE AUDIO ---"
    if [ -f "$OUTPUT_DIR/audio_analysis.log" ]; then
        grep -E "(mean_volume|max_volume)" "$OUTPUT_DIR/audio_analysis.log" || echo "No se encontraron métricas de audio"
    fi
    
    echo ""
    echo "--- DETECCIÓN DE ARTIFACTS ---"
    if [ -f "$OUTPUT_DIR/artifact_detection.log" ]; then
        grep -E "(black_detect|black_frame)" "$OUTPUT_DIR/artifact_detection.log" || echo "No se detectaron artifacts"
    fi
    
} > "$OUTPUT_DIR/quality_report.txt"

echo "✓ Reporte resumido guardado en $OUTPUT_DIR/quality_report.txt"

echo ""
echo "=== ANÁLISIS COMPLETADO ==="
echo "Todos los archivos de análisis están en: $OUTPUT_DIR/"
echo "Reporte principal: $OUTPUT_DIR/quality_report.txt"
echo ""
echo "Para análisis más avanzado con VMAF:"
echo "  pip install vmaf"
echo "  ffmpeg -i $INPUT_FILE -i reference.mp4 -lavfi libvmaf -f null -" 