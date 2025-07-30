# Stream Analysis Tools - Herramientas de Análisis de Streams

Este directorio contiene herramientas especializadas para analizar la calidad, latencia y adaptación de streams DASH/HLS en tiempo real.

## 🎯 Herramientas Disponibles

### 1. **Stream Quality Analyzer** (`stream_quality_analyzer.py`)
Analiza la calidad de video de los segmentos del stream usando métricas como SSIM, bitrate, y análisis de frames.

**Características:**
- Análisis SSIM de segmentos de video
- Métricas de bitrate y resolución
- Análisis de codecs y formatos
- Descarga temporal de segmentos para análisis

**Uso:**
```bash
python3 stream_quality_analyzer.py <manifest_url> [-o output_dir] [-i interval]
```

### 2. **Stream Latency Analyzer** (`stream_latency_analyzer.py`)
Mide la latencia de respuesta del manifest y descarga de segmentos para detectar problemas de buffering.

**Características:**
- Medición de latencia del manifest
- Análisis de latencia de descarga de segmentos
- Detección de timeouts y errores
- Métricas de estabilidad de red

**Uso:**
```bash
python3 stream_latency_analyzer.py <manifest_url> [-o output_dir] [-i interval]
```

### 3. **Stream Adaptation Analyzer** (`stream_adaptation_analyzer.py`)
Analiza el comportamiento de adaptación de bitrate y detecta eventos de switching.

**Características:**
- Análisis de adaptación de bitrate
- Detección de eventos de switching (upgrade/downgrade)
- Gráficos de evolución temporal
- Métricas de estabilidad de adaptación

**Uso:**
```bash
python3 stream_adaptation_analyzer.py <manifest_url> [-o output_dir] [-i interval]
```

### 4. **Stream Analysis Suite** (`stream_analysis_suite.py`)
Suite completa que integra todas las herramientas de análisis en una sola interfaz.

**Características:**
- Análisis simultáneo de calidad, latencia y adaptación
- Dashboard integrado con métricas agregadas
- Reportes comprehensivos
- Health score general del stream

**Uso:**
```bash
# Suite completa
python3 stream_analysis_suite.py <manifest_url> [-o output_dir] [-i interval]

# Solo análisis específico
python3 stream_analysis_suite.py <manifest_url> --quality-only
python3 stream_analysis_suite.py <manifest_url> --latency-only
python3 stream_analysis_suite.py <manifest_url> --adaptation-only
```

## 🚀 Ejemplos de Uso

### Análisis Básico de Calidad
```bash
# Analizar calidad cada 30 segundos
python3 stream_quality_analyzer.py http://localhost:38880/output/manifest.mpd -i 30

# Guardar resultados en directorio específico
python3 stream_quality_analyzer.py http://localhost:38880/output/manifest.mpd -o ./my_analysis
```

### Análisis de Latencia en Tiempo Real
```bash
# Medir latencia cada 5 segundos
python3 stream_latency_analyzer.py http://localhost:38880/output/manifest.mpd -i 5
```

### Análisis de Adaptación con Gráficos
```bash
# Analizar adaptación cada 10 segundos (genera gráficos)
python3 stream_adaptation_analyzer.py http://localhost:38880/output/manifest.mpd -i 10
```

### Suite Completa de Análisis
```bash
# Ejecutar todos los análisis simultáneamente
python3 stream_analysis_suite.py http://localhost:38880/output/manifest.mpd -i 30
```

## 📊 Métricas y Reportes

### Métricas de Calidad
- **SSIM (Structural Similarity Index)**: Medida de similitud estructural (0-1, mayor es mejor)
- **Bitrate promedio**: Bitrate promedio de los segmentos analizados
- **Resolución**: Resolución de los segmentos de video
- **Codec**: Información del codec utilizado

### Métricas de Latencia
- **Latencia del manifest**: Tiempo de respuesta del archivo MPD
- **Latencia de segmentos**: Tiempo de descarga de segmentos
- **Tasa de timeout**: Porcentaje de timeouts
- **Tasa de error**: Porcentaje de errores de red

### Métricas de Adaptación
- **Estabilidad de bitrate**: Score de estabilidad (0-1)
- **Eventos de switching**: Número de cambios de bitrate
- **Frecuencia de switching**: Frecuencia de cambios
- **Dirección de cambios**: Upgrades vs downgrades

### Health Score General
- **Stream Health Score**: Puntuación general del stream (0-1)
- **Quality Score**: Puntuación de calidad
- **Latency Score**: Puntuación de latencia
- **Adaptation Score**: Puntuación de adaptación

## 📁 Estructura de Archivos de Salida

```
stream_analysis/
├── quality/
│   ├── stream_quality_analysis.json
│   └── quality_report.txt
├── latency/
│   ├── latency_analysis.json
│   └── latency_report.txt
├── adaptation/
│   ├── adaptation_analysis.json
│   ├── adaptation_report.txt
│   └── bitrate_adaptation.png
├── analysis_suite.json
├── comprehensive_report.txt
└── dashboard_data.json
```

## 🔧 Configuración del Docker

Para usar estas herramientas dentro del contenedor Docker:

```bash
# Entrar al contenedor
docker exec -it monitor bash

# Ejecutar análisis desde dentro del contenedor
python3 /app/stream_analysis_suite.py http://player:80/output/manifest.mpd -i 30
```

## 📈 Dashboard Integration

Los datos generados por las herramientas se integran automáticamente con el dashboard web:

- **Dashboard URL**: http://localhost:38881
- **Player URL**: http://localhost:38880

El dashboard muestra:
- Health score general del stream
- Métricas de calidad, latencia y adaptación
- Recomendaciones automáticas
- Estado en tiempo real

## 🛠️ Dependencias

Las herramientas requieren las siguientes dependencias (ya incluidas en el Dockerfile):

```python
requests          # Para HTTP requests
matplotlib        # Para generación de gráficos
numpy             # Para cálculos numéricos
xml.etree         # Para parsing de MPD (incluido en Python)
```

## 🔍 Troubleshooting

### Problemas Comunes

1. **Error de conexión al manifest**
   - Verificar que el stream esté activo
   - Comprobar la URL del manifest
   - Verificar conectividad de red

2. **No se encuentran segmentos**
   - El stream puede no estar generando segmentos
   - Verificar configuración del packager
   - Comprobar logs del contenedor

3. **Análisis SSIM falla**
   - Los segmentos pueden ser muy cortos
   - Verificar que FFmpeg esté instalado
   - Comprobar permisos de escritura en /tmp

### Logs y Debugging

```bash
# Ver logs del contenedor
docker logs monitor

# Ver logs específicos de análisis
tail -f stream_analysis/comprehensive_report.txt

# Verificar archivos generados
ls -la stream_analysis/
```

## 📝 Notas Importantes

1. **Rendimiento**: Los análisis de calidad son intensivos en CPU. Ajusta el intervalo según tus necesidades.

2. **Almacenamiento**: Los archivos de análisis pueden crecer rápidamente. Considera limpiar periódicamente.

3. **Red**: Las herramientas descargan segmentos temporalmente. Asegúrate de tener suficiente ancho de banda.

4. **Tiempo Real**: Estas herramientas están diseñadas para análisis en tiempo real, no para archivos de video estáticos.

## 🤝 Contribuciones

Para agregar nuevas métricas o herramientas:

1. Crea un nuevo analizador siguiendo el patrón de los existentes
2. Integra el analizador en `stream_analysis_suite.py`
3. Actualiza este README con la documentación
4. Prueba con diferentes tipos de streams

## 📞 Soporte

Para problemas o preguntas:
- Revisa los logs del contenedor
- Verifica la configuración del stream
- Consulta la documentación de FFmpeg para análisis avanzado 