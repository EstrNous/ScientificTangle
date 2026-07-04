FROM nginx:alpine

RUN apk add --no-cache apache2-utils gettext

COPY nginx.dev.conf /etc/nginx/nginx.dev.conf
COPY nginx.prod.conf.template /etc/nginx/nginx.prod.conf.template
COPY nginx.dev.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
