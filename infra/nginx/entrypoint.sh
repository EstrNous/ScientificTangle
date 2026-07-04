#!/bin/sh
set -e

htpasswd -cb /etc/nginx/grafana.htpasswd \
  "${GRAFANA_NGINX_BASIC_USER:-grafana}" \
  "${GRAFANA_NGINX_BASIC_PASSWORD:-grafana123}"

if [ "${NGINX_CONFIG:-dev}" = "cloud" ]; then
  if [ ! -f /etc/nginx/nginx.conf ] || [ ! -s /etc/nginx/nginx.conf ]; then
    cp /etc/nginx/nginx.cloud.http.conf /etc/nginx/nginx.conf
  fi
fi

if [ "${NGINX_CONFIG:-dev}" = "prod" ]; then
  export NGINX_SERVER_NAME="${NGINX_SERVER_NAME:-localhost}"
  export TLS_CERT_FILE="${TLS_CERT_FILE:-/etc/nginx/tls/fullchain.pem}"
  export TLS_KEY_FILE="${TLS_KEY_FILE:-/etc/nginx/tls/privkey.pem}"
  envsubst '${NGINX_SERVER_NAME} ${TLS_CERT_FILE} ${TLS_KEY_FILE}' \
    < /etc/nginx/nginx.prod.conf.template > /etc/nginx/nginx.conf
fi

exec nginx -g 'daemon off;'
