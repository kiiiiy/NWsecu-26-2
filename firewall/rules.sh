#!/bin/sh
set -eu
OUTSIDE=$(ip -o -4 addr show | awk '$4 == "172.28.10.2/24" {print $2}')
INSIDE=$(ip -o -4 addr show | awk '$4 == "172.28.20.2/24" {print $2}')
test -n "$OUTSIDE" && test -n "$INSIDE"

iptables -F
iptables -t nat -F
iptables -X
iptables -N AUDIT_ALLOW
iptables -A AUDIT_ALLOW -j NFLOG --nflog-group 10 --nflog-prefix ALLOW --nflog-threshold 1
iptables -A AUDIT_ALLOW -j ACCEPT
iptables -N AUDIT_BLOCK
iptables -A AUDIT_BLOCK -j NFLOG --nflog-group 10 --nflog-prefix BLOCK --nflog-threshold 1
iptables -A AUDIT_BLOCK -j DROP

iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m conntrack --ctstate INVALID -j AUDIT_BLOCK
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
for cidr in $ADMIN_CIDRS; do
    iptables -A INPUT -i "$OUTSIDE" -s "$cidr" -p tcp --dport 22 -m conntrack --ctstate NEW -j AUDIT_ALLOW
done
iptables -A INPUT -j AUDIT_BLOCK

iptables -A FORWARD -m conntrack --ctstate INVALID -j AUDIT_BLOCK
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -i "$OUTSIDE" -o "$INSIDE" -d 172.28.20.10 -p tcp --dport 80 -m conntrack --ctstate NEW -j AUDIT_ALLOW
iptables -A FORWARD -j AUDIT_BLOCK

iptables -t nat -A PREROUTING -i "$OUTSIDE" -d 172.28.10.2 -p tcp --dport 80 -j DNAT --to-destination 172.28.20.10:80
iptables -t nat -A POSTROUTING -o "$INSIDE" -d 172.28.20.10 -p tcp --dport 80 -j SNAT --to-source 172.28.20.2
iptables-save > /var/log/firewall/active-rules.txt
sed -i '/^# /d' /var/log/firewall/active-rules.txt
