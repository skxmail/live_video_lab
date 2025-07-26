#!/bin/sh
set -e



YOUTUBE_URL="https://www.youtube.com/watch?v=cb12KmMMDJA"
STREAM_URL=$(yt-dlp -g -f best "$YOUTUBE_URL")

# ffmpeg -i ./media/output/capture.mp4 -c:v libx264 -preset veryfast -s 640x360 -b:v 800k -c:a aac -b:a 128k ./media/output/capture2.mp4
ffmpeg -i "$STREAM_URL" -c:v libx264 -preset veryfast -s 1920x1080 -b:v 800k -c:a aac -b:a 128k -f mpegts udp://172.28.1.11:40000 
# ffmpeg -i "$STREAM_URL" -c:v libx264 -preset veryfast -s 640x360 -b:v 800k -c:a aac -b:a 128k -f mpegts udp://0.0.0.0:40000 
# ffmpeg -i "$STREAM_URL"  -f mpegts udp://0.0.0.0:40000 