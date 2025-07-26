#!/bin/bash
set -e

YOUTUBE_URL="https://www.youtube.com/watch?v=cb12KmMMDJA"
WWW_DIR="$(pwd)/media/www"

# 1. Obtener la URL directa del stream con yt-dlp
STREAM_URL=$(yt-dlp -g -f best "$YOUTUBE_URL")

# 2. Lanzar ffmpeg en background (publica en UDP en la red de Docker)
docker compose run --rm  --name encoder_runner \
  encoder -i "$STREAM_URL" -f mpegts udp://0.0.0.0:40000 #&

# FFMPEG_PID=$!

# # 3. Esperar unos segundos para que ffmpeg comience a emitir
# sleep 5

# # 4. Lanzar shaka-packager para consumir el UDP desde el contenedor ffmpeg
# docker compose run --rm shaka-packager packager \
#   input=udp://ffmpeg:40000,stream=video,output=/media/www/video.mp4 \
#   input=udp://ffmpeg:40000,stream=audio,output=/media/www/audio.mp4 \
#   --mpd_output /media/www/manifest.mpd

# # 5. Detener ffmpeg
# kill $FFMPEG_PID

# echo "[Listo] Abre http://localhost:8080 en tu navegador para ver el stream capturado." 