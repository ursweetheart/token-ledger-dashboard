FROM nginx:1.27-alpine
RUN apk add --no-cache nodejs bash tini su-exec
ENV LLM_GATEWAY_DOMAIN=apigateway.rangdong.com.vn \
    LLM_GATEWAY_ADMIN_CIDR=127.0.0.1/32 \
    NGINX_ENVSUBST_FILTER=^LLM_GATEWAY_(DOMAIN|ADMIN_CIDR)$ \
    STATUS_BIND=127.0.0.1 STATUS_PORT=8089
COPY tools/gateway-status/server.js tools/gateway-status/index.html tools/gateway-status/app.js tools/gateway-status/style.css /app/
COPY docker/gateway/nginx.conf /etc/nginx/templates/default.conf.template
COPY docker/gateway/lb-entrypoint.sh /lb-entrypoint.sh
ENTRYPOINT ["/sbin/tini", "--", "/bin/bash", "/lb-entrypoint.sh"]
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=10s --timeout=5s --retries=6 CMD wget -q -O- http://127.0.0.1:4000/lb-health | grep -q lb-ok && wget -q -O /dev/null http://127.0.0.1:8089/
