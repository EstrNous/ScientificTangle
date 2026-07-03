FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY public/index.html /usr/share/nginx/html/index.html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:3000/ || exit 1
