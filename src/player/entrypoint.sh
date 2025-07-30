#!/bin/sh
sed -i "s|__MANIFEST_URL__|${MANIFEST_URL}|g" /usr/share/nginx/html/index.html
exec nginx -g 'daemon off;'