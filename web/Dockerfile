FROM nginx:stable-alpine
RUN apk add --no-cache iproute2
COPY index.html /usr/share/nginx/html/index.html
COPY route.sh /docker-entrypoint.d/05-route.sh
RUN chmod +x /docker-entrypoint.d/05-route.sh
