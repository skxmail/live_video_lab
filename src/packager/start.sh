#!/bin/sh

# Ejecutar packager en segundo plano
/usr/bin/packager $PACKAGER_PARAMS &
PACKAGER_PID=$!

# Iniciar nginx en primer plano
nginx -g 'daemon off;'