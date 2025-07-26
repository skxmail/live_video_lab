#!/bin/bash
set -e


WWW_DIR="$(pwd)/media/www"


# docker compose run --rm packager packager \
#   'input=udp://172.24.2.40:40000,stream=video,init_segment=audio_init.mp4,segment_template=audio_$Number$.m4s' \
#   'input=udp://172.24.2.40:40000,stream=audio,init_segment=h264_360p_init.mp4,segment_template=h264_360p_$Number$.m4s' \
#   --mpd_output /media/www/manifest.mpd

docker run --rm google/shaka-packager:v3.4.2 ping 172.24.2.40
docker run --rm google/shaka-packager:v3.4.2 packager \
  'input=udp://172.24.2.10:40000,stream=video,init_segment=audio_init.mp4,segment_template=audio_$Number$.m4s' \
  'input=udp://172.24.2.10:40000,stream=audio,init_segment=h264_360p_init.mp4,segment_template=h264_360p_$Number$.m4s' \
  --mpd_output /media/www/manifest.mpd


packager 'input=udp://0.0.0.0:40000,stream=video,init_segment=audio_init.mp4,segment_template=audio_$Number$.m4s' 'input=udp://0.0.0.0:40000,stream=audio,init_segment=h264_360p_init.mp4,segment_template=h264_360p_$Number$.m4s' --mpd_output /media/www/manifest.mpd