FROM nginx:1.28-alpine

COPY docker/nginx.local.conf /etc/nginx/conf.d/default.conf
COPY web/ /usr/share/nginx/html/

EXPOSE 80 443
