FROM debian:bookworm-slim
RUN apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::ForceIPv4=true update && apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=30 install -y --no-install-recommends iptables iproute2 openssh-server python3 ca-certificates sshpass sudo && rm -rf /var/lib/apt/lists/* && rm -f /etc/ssh/ssh_host_*
COPY . /opt/firewall/
RUN chmod +x /opt/firewall/*.sh
ENTRYPOINT ["/opt/firewall/entrypoint.sh"]
