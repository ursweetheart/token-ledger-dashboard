# nginx serving web/ and proxying /api/ to the api container.
# Named "web", not "gateway": since 27/08 that word means the LiteLLM API
# Gateway in this project, and docker/gateway/ already exists.

FROM nginx:1.28-alpine

COPY docker/nginx.dashboard.conf /etc/nginx/conf.d/default.conf
COPY web/ /usr/share/nginx/html/

EXPOSE 80
