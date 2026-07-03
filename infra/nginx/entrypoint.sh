#!/bin/sh
set -e

htpasswd -cb /etc/nginx/grafana.htpasswd \
  "${GRAFANA_NGINX_BASIC_USER:-grafana}" \
  "${GRAFANA_NGINX_BASIC_PASSWORD:-grafana123}"

exec nginx -g 'daemon off;'
