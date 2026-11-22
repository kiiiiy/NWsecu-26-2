FROM nginx:stable-alpine

RUN apk add --no-cache iproute2

COPY html/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY route.sh /docker-entrypoint.d/05-route.sh
RUN chmod +x /docker-entrypoint.d/05-route.sh

EXPOSE 80