#!/bin/sh
set -eu

# 1. 환경변수를 검사하고 관리자 계정을 준비한다.
python3 /opt/firewall/validate.py
mkdir -p /run/sshd /var/log/firewall
id "$ADMIN_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$ADMIN_USER"
printf '%s:%s\n' "$ADMIN_USER" "$ADMIN_PASSWORD" | chpasswd
printf '%s ALL=(root) /usr/sbin/iptables, /usr/sbin/iptables-save\n' "$ADMIN_USER" > /etc/sudoers.d/firewall-admin
chmod 440 /etc/sudoers.d/firewall-admin
visudo -cf /etc/sudoers.d/firewall-admin
ssh-keygen -A
cat > /etc/ssh/sshd_config <<EOF
Port 22
ListenAddress 0.0.0.0
PasswordAuthentication yes
KbdInteractiveAuthentication no
PermitRootLogin no
AllowUsers $ADMIN_USER
UsePAM yes
AllowTcpForwarding no
AllowAgentForwarding no
X11Forwarding no
PermitTunnel no
PidFile /run/sshd.pid
Subsystem sftp internal-sftp
EOF
rm -f /run/firewall.ready /run/nflog.ready

# 2. 서비스가 열리기 전에 기본 정책을 차단으로 설정한다.
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT
# 3. 로그 수집이 준비된 뒤에만 허용 규칙과 SSH를 시작한다.
python3 -u /opt/firewall/logger.py &
LOGGER_PID=$!
echo "$LOGGER_PID" > /run/logger.pid
trap 'kill "$LOGGER_PID" "${SSH_PID:-}" 2>/dev/null || true' EXIT INT TERM
attempts=0
while [ ! -f /run/nflog.ready ]; do
    kill -0 "$LOGGER_PID"
    attempts=$((attempts+1))
    if [ "$attempts" -ge 100 ]; then
        echo '로그 수집기 시작 시간 초과' >&2
        exit 1
    fi
    sleep 0.1
done
/opt/firewall/rules.sh
/usr/sbin/sshd -D -e &
SSH_PID=$!
touch /run/firewall.ready
# 4. 둘 중 하나라도 종료되면 컨테이너도 종료한다.
while kill -0 "$LOGGER_PID" && kill -0 "$SSH_PID"; do
    sleep 1
done
exit 1
