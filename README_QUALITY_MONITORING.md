# Herramientas de Monitoreo de Calidad para Streaming DASH/HLS

Este conjunto de herramientas te permite analizar y monitorear la calidad de señales de streaming DASH y HLS, detectando problemas como macroblocking, cortes, problemas de audio, lipsync, etc.

## 🛠️ Herramientas Incluidas

### 1. **Monitor Web en Tiempo Real** (`media/www/quality_monitor.html`)
- Interfaz web que muestra métricas en tiempo real
- Monitorea bitrate, resolución, FPS, buffer health
- Log de eventos de adaptación y errores
- Accesible en `http://localhost:8080/quality_monitor.html`

### 2. **Analizador de Calidad FFmpeg** (`quality_analyzer.sh`)
- Script bash para análisis profundo de archivos de video
- Métricas: PSNR, SSIM, signalstats, audio analysis
- Detección de artifacts y macroblocking
- Genera reportes detallados

### 3. **Monitor de Stream Python** (`stream_monitor.py`)
- Monitoreo continuo de manifests DASH/HLS
- Análisis de bitrates, resoluciones, codecs
- Verificación de accesibilidad de segmentos
- Logs detallados y reportes JSON

## 🚀 Instalación y Uso

### Opción 1: Usando Docker (Recomendado)

```bash
# Iniciar todo el sistema de monitoreo
./start_monitoring.sh

# Esto construirá la imagen y iniciará todos los servicios:
# - Encoder (FFmpeg)
# - Packager (Shaka Packager)
# - Player (Nginx)
# - Monitor (Herramientas de calidad)
```

**URLs de acceso:**
- Player: http://localhost:8080
- Monitor Dashboard: http://localhost:8081
- Quality Monitor: http://localhost:8080/quality_monitor.html

### Opción 2: Instalación Manual

#### Prerrequisitos

```bash
# Instalar dependencias básicas
sudo apt-get update
sudo apt-get install -y ffmpeg jq python3-pip

# Instalar dependencias Python
pip3 install requests

# Para análisis avanzado con VMAF (opcional)
pip3 install vmaf
```

### 1. Monitor Web

```bash
# Acceder al monitor web
# Asegúrate de que tu stream esté funcionando
docker compose up -d
# Luego visita: http://localhost:8080/quality_monitor.html
```

### 2. Analizador de Calidad

```bash
# Hacer ejecutable el script
chmod +x quality_analyzer.sh

# Analizar un archivo de video
./quality_analyzer.sh ./media/www/h264_360p_1.m4s ./quality_logs

# Analizar con archivo de referencia (para PSNR)
cp original_video.mp4 reference.mp4
./quality_analyzer.sh ./media/www/h264_360p_1.m4s ./quality_logs
```

### 3. Monitor de Stream

```bash
# Hacer ejecutable el script
chmod +x stream_monitor.py

# Monitorear stream DASH
python3 stream_monitor.py http://localhost:8080/manifest.mpd -i 10 -d 300

# Monitorear stream HLS
python3 stream_monitor.py http://example.com/stream.m3u8 -i 30

# Parámetros:
# -i: intervalo en segundos (default: 30)
# -d: duración total en segundos (opcional)
# -o: archivo de salida personalizado
```

### 4. Análisis Automático de Calidad

```bash
# Análisis único de segmentos
./auto_quality_check.sh

# Monitoreo continuo cada 5 minutos
./auto_quality_check.sh continuous

# Monitoreo cada minuto
./auto_quality_check.sh continuous 60

# Limpiar logs antiguos (más de 7 días)
./auto_quality_check.sh cleanup

# Ver ayuda
./auto_quality_check.sh help
```

## 📊 Métricas que se Monitorean

### Video
- **Bitrate**: Actual, mínimo, máximo, promedio
- **Resolución**: Cambios de resolución en tiempo real
- **FPS**: Frames por segundo
- **Buffer Health**: Estado del buffer de reproducción
- **Dropped Frames**: Frames perdidos
- **PSNR**: Peak Signal-to-Noise Ratio (con referencia)
- **SSIM**: Structural Similarity Index
- **Macroblocking**: Detección de artifacts de compresión

### Audio
- **Nivel de Audio**: Volumen medio y máximo
- **Codec**: Tipo de codec de audio
- **Bitrate**: Bitrate de audio
- **Lipsync**: Sincronización audio-video

### Streaming
- **Adaptación**: Cambios de calidad automáticos
- **Latencia de Red**: Tiempo de respuesta del servidor
- **Disponibilidad**: Accesibilidad de segmentos
- **Errores**: Errores de red y reproducción

## 🔍 Herramientas Externas Recomendadas

### 1. **VMAF (Video Multi-method Assessment Fusion)**
```bash
# Instalación
git clone https://github.com/Netflix/vmaf.git
cd vmaf
make
sudo make install

# Uso
ffmpeg -i input.mp4 -i reference.mp4 -lavfi libvmaf -f null -
```

### 2. **FFmpeg con filtros avanzados**
```bash
# Análisis de calidad perceptual
ffmpeg -i input.mp4 -vf "ssim=stats_file=ssim.log" -f null -

# Detección de black frames
ffmpeg -i input.mp4 -vf "blackdetect=d=0.1:pix_th=0.1" -f null -

# Análisis de audio
ffmpeg -i input.mp4 -af "volumedetect" -f null -
```

### 3. **MP4Box (GPAC)**
```bash
# Instalación
sudo apt-get install gpac

# Análisis de estructura MP4
mp4box -info input.mp4
mp4box -std input.mp4
```

### 4. **Bento4**
```bash
# Instalación
git clone https://github.com/axiomatic-systems/Bento4.git
cd Bento4
mkdir cmakebuild && cd cmakebuild
cmake ..
make

# Análisis de DASH
mp4dash --analyze manifest.mpd
```

## 📈 Interpretación de Resultados

### PSNR (Peak Signal-to-Noise Ratio)
- **> 40 dB**: Excelente calidad
- **30-40 dB**: Buena calidad
- **20-30 dB**: Calidad aceptable
- **< 20 dB**: Calidad pobre

### SSIM (Structural Similarity Index)
- **0.95-1.0**: Excelente similitud
- **0.90-0.95**: Buena similitud
- **0.80-0.90**: Similitud aceptable
- **< 0.80**: Similitud pobre

### Buffer Health
- **> 5 segundos**: Buffer saludable
- **2-5 segundos**: Buffer normal
- **< 2 segundos**: Buffer bajo (riesgo de buffering)

## 🐛 Detección de Problemas Comunes

### Macroblocking
```bash
# Usar filtros de detección
ffmpeg -i input.mp4 -vf "signalstats=stats=1:out=1" -f null -
```

### Cortes y Black Frames
```bash
# Detectar frames negros
ffmpeg -i input.mp4 -vf "blackdetect=d=0.1:pix_th=0.1" -f null -
```

### Problemas de Audio
```bash
# Análisis de volumen
ffmpeg -i input.mp4 -af "volumedetect" -f null -

# Detectar silencios
ffmpeg -i input.mp4 -af "silencedetect=noise=-50dB:d=0.5" -f null -
```

### Lipsync
```bash
# Comparar timestamps de audio y video
ffprobe -v quiet -show_entries stream=start_time,time_base -of json input.mp4
```

## 📝 Logs y Reportes

### Estructura de Archivos Generados
```
quality_logs/
├── file_info.json          # Información básica del archivo
├── psnr.log               # Métricas PSNR
├── ssim.log               # Métricas SSIM
├── signalstats.log        # Estadísticas de señal
├── audio_analysis.log     # Análisis de audio
├── artifact_detection.log # Detección de artifacts
├── frame_analysis.log     # Análisis de frames
└── quality_report.txt     # Reporte resumido
```

### Formato de Logs JSON
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "manifest_url": "http://localhost:8080/manifest.mpd",
  "manifest_info": {
    "type": "DASH",
    "video_streams": 3,
    "audio_streams": 1,
    "bitrates": [800000, 1500000, 2500000]
  },
  "network_info": {
    "status": "ok",
    "response_time": 0.123
  }
}
```

## 🔧 Integración con tu Pipeline

### Docker Compose
El servicio de monitoreo ya está integrado en tu `docker-compose.yaml`:

```yaml
monitor:
  build:
    context: .
    dockerfile: Dockerfile.monitor
  container_name: monitor
  volumes:
    - ./media:/media
    - ./logs:/app/logs
    - ./quality_analyzer.sh:/app/quality_analyzer.sh:ro
    - ./stream_monitor.py:/app/stream_monitor.py:ro
  ports:
    - "8081:8081"
  environment:
    - MANIFEST_URL=http://packager:8080/manifest.mpd
    - MONITOR_INTERVAL=30
    - LOG_LEVEL=INFO
  networks:
    - streaming
  depends_on:
    - packager
  command: ["python3", "/app/stream_monitor.py", "http://packager:8080/manifest.mpd", "-i", "30", "-o", "/app/logs/stream_quality.json"]
```

### Imagen Docker Personalizada
La imagen `Dockerfile.monitor` incluye:
- FFmpeg con todos los codecs
- VMAF (Video Multi-method Assessment Fusion)
- GPAC (MP4Box)
- Bento4 (herramientas DASH)
- Python con librerías de análisis
- Dashboard web integrado

### Scripts de Automatización

#### Inicio del Sistema
```bash
#!/bin/bash
# start_monitoring.sh

# Construir imagen de monitoreo
docker build -f Dockerfile.monitor -t streaming-monitor .

# Iniciar todos los servicios
docker compose up -d

# Verificar estado
docker compose ps
```

#### Análisis Automático
```bash
#!/bin/bash
# auto_quality_check.sh

# Análisis continuo de segmentos
./auto_quality_check.sh continuous 300  # Cada 5 minutos

# Limpieza automática
./auto_quality_check.sh cleanup 7       # Mantener 7 días
```

#### Comandos Útiles
```bash
# Ver logs del monitor
docker compose logs -f monitor

# Analizar segmento específico
docker exec monitor ./quality_analyzer.sh /media/www/h264_360p_1.m4s /app/logs

# Ver métricas en tiempo real
cat logs/stream_quality.json | jq '.[-1]'

# Acceder al contenedor para análisis manual
docker exec -it monitor bash
```

## 🎯 Casos de Uso

### 1. **Monitoreo Continuo de Producción**
```bash
# Monitorear 24/7 con rotación de logs
python3 stream_monitor.py http://prod-server/stream.mpd -i 60 -o /var/log/stream_quality.json
```

### 2. **Análisis de Calidad Post-Producción**
```bash
# Analizar archivos completos
for file in *.mp4; do
  ./quality_analyzer.sh "$file" "./analysis/$(basename "$file" .mp4)"
done
```

### 3. **Comparación A/B de Codecs**
```bash
# Comparar H.264 vs H.265
./quality_analyzer.sh h264_output.mp4 ./comparison/h264
./quality_analyzer.sh h265_output.mp4 ./comparison/h265
```

## 📚 Recursos Adicionales

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [VMAF GitHub](https://github.com/Netflix/vmaf)
- [Shaka Player Events](https://shaka-player-demo.appspot.com/docs/api/tutorial-events.html)
- [DASH-IF Guidelines](https://dashif.org/guidelines/)

## 🤝 Contribuciones

Si encuentras problemas o quieres agregar nuevas métricas, puedes:
1. Crear un issue en el repositorio
2. Proponer mejoras a los scripts
3. Agregar nuevos filtros de análisis

---

**Nota**: Estas herramientas están diseñadas para complementar tu pipeline de Shaka Packager y proporcionar visibilidad completa de la calidad de tu streaming. 