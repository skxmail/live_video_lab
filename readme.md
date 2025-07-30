# Shaka Packager Streaming Quality Suite

Este proyecto es una suite de herramientas para **empaquetado, monitoreo y análisis de calidad de streaming** de video, basada en contenedores Docker. Permite simular flujos de video, empaquetarlos en DASH, reproducirlos y monitorear métricas de calidad en tiempo real.

## Componentes principales

- **encoder**: Descarga y transcodifica streams (por ejemplo, de YouTube) usando FFmpeg.
- **packager**: Empaqueta los streams en formato DASH (manifest.mpd) para distribución.
- **player**: Reproduce el stream DASH en un navegador usando Shaka Player y muestra métricas de calidad.
- **monitor**: Analiza la calidad del stream (bitrate, latencia, adaptación, SSIM, etc.) y guarda logs.
- **dashboard**: Interfaz web para visualizar métricas y gráficos de calidad de streaming en tiempo real.

## Estructura del repositorio

```
.
├── Dockerfile.encoder
├── Dockerfile.packager
├── Dockerfile.player
├── Dockerfile.monitor
├── Dockerfile.dashboard
├── docker-compose.yaml
├── src/
│   ├── encoder/
│   │   └── start_encoder.sh
│   ├── monitor/
│   │   ├── stream_analysis_suite.py
│   │   ├── stream_analysis_common.py
│   │   └── ...
│   ├── player/
│   │   └── quality_monitor.html
│   └── dashboard/
│       └── dashboard.py
└── temp-data/
```

## Uso rápido

1. **Clona el repositorio**
   ```sh
   git clone https://github.com/tu_usuario/shaka_packager.git
   cd shaka_packager
   ```

2. **Configura las variables de entorno en `docker-compose.yaml`**
   - Cambia `YOUTUBE_URL` por el video que quieras simular.
   - Cambia `MANIFEST_URL` por la URL del manifest que el player debe reproducir.

3. **Levanta todos los servicios**
   ```sh
   docker-compose up --build
   ```

4. **Accede a las interfaces**
   - **Player:** [http://localhost:38880](http://localhost:38880)
   - **Dashboard:** [http://localhost:38881](http://localhost:38881)

## Personalización

- Puedes cambiar el stream de entrada modificando la variable `YOUTUBE_URL` en el servicio `encoder` de `docker-compose.yaml`.
- Puedes cambiar el manifest reproducido por el player modificando `MANIFEST_URL` en el servicio `player`.
- Los logs y métricas se almacenan en el directorio `temp-data/packager-output` y en `/app/stream_analysis/` dentro del contenedor monitor.

## Métricas y análisis

- **Bitrate, resolución, FPS, buffer health, dropped frames**: Visualizados en el player.
- **SSIM, latencia, adaptación de bitrate**: Calculados por el monitor y graficados en el dashboard.
- **Logs tabulares**: Exportados en CSV y JSON para análisis posterior.

## Requisitos

- Docker y Docker Compose instalados.
- Puertos 38880, 38881 y 38882 libres en tu máquina o cambiarlos en el docker-compose.yaml

## Créditos

- [Shaka Player](https://github.com/shaka-project/shaka-player)
- [FFmpeg](https://ffmpeg.org/)
- [Plotly](https://plotly.com/)
- [Flask](https://flask.palletsprojects.com/)

---

**Proyecto para monitoreo y análisis de calidad de streaming