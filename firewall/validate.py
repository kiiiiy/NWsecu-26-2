import ipaddress
import os
import re

username = os.environ.get("ADMIN_USER", "")
if not re.fullmatch(r"[a-z][a-z0-9_-]{0,30}", username):
    raise SystemExit("ADMIN_USER must be a normal lowercase Linux username")
password = os.environ.get("ADMIN_PASSWORD", "")
if len(password) < 12 or password == "CHANGE_ME" or any(c in password for c in "\r\n:"):
    raise SystemExit("Set ADMIN_PASSWORD to 12+ characters without newline or colon")
admin_networks = os.environ.get("ADMIN_CIDRS", "").split()
if not admin_networks:
    raise SystemExit("ADMIN_CIDRS requires one or more space-separated IPv4 CIDRs")
for address in admin_networks:
    network = ipaddress.ip_network(address, strict=True)
    if network.version != 4 or network.prefixlen == 0:
        raise SystemExit("Use specific IPv4 CIDRs; 0.0.0.0/0 is prohibited")
