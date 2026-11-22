"""Integration checks from distinct source IPs on the outside network."""
import os
import json
import socket
import subprocess
import time
import urllib.request

target = "172.28.10.2"
for attempt in range(20):
    try:
        with urllib.request.urlopen(f"http://{target}/", timeout=2) as response:
            assert response.status == 200
            assert "TEAM 8" in response.read().decode()
        break
    except (OSError, AssertionError):
        if attempt == 19:
            raise
        time.sleep(0.5)
print("PASS HTTP through firewall")

def get_api(endpoint):
    with urllib.request.urlopen(f"http://{target}/api/{endpoint}", timeout=3) as response:
        assert response.status == 200
        return json.load(response)

assert get_api("status")["status"] == "ONLINE"
print("PASS API through Nginx and firewall")
allow = os.environ["EXPECT_SSH"] == "allow"
try:
    with socket.create_connection((target, 22), timeout=2) as conn:
        banner = conn.recv(256)
        assert allow, "Non-admin source reached SSH"
        assert banner.startswith(b"SSH-2.0-OpenSSH")
except TimeoutError:
    assert not allow, "Admin source could not reach SSH"
print("PASS SSH source restriction:", "ALLOW" if allow else "BLOCK")
if allow:
    command = ["sshpass", "-e", "ssh", "-o", "StrictHostKeyChecking=no",
               "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=3",
               f"{os.environ['ADMIN_USER']}@{target}", "id -un"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
    assert result.stdout.strip() == os.environ["ADMIN_USER"]
    print("PASS admin password authentication")
    managed = command[:-1] + ["sudo -S /usr/sbin/iptables -S"]
    result = subprocess.run(managed, input=os.environ["SSHPASS"] + "\n", capture_output=True, text=True, timeout=10, check=True)
    assert "-P INPUT DROP" in result.stdout and "-P FORWARD DROP" in result.stdout
    print("PASS authenticated firewall administration")
    wrong = dict(os.environ, SSHPASS="deliberately-incorrect-test-password")
    result = subprocess.run(command, env=wrong, capture_output=True, text=True, timeout=15)
    assert result.returncode == 5, f"Expected authentication rejection, got {result.returncode}"
    print("PASS wrong password rejected")
for host, port in [(target, 81), (target, 3000), ("172.28.20.10", 80), ("172.28.20.20", 3000)]:
    try:
        with socket.create_connection((host, port), timeout=2):
            raise AssertionError(f"Unexpected direct access: {host}:{port}")
    except (TimeoutError, ConnectionRefusedError, OSError) as exc:
        if host == target:
            assert isinstance(exc, TimeoutError), f"Expected firewall DROP timeout, got {exc}"
    print("PASS denied:", host, port)

events = get_api("logs")["logs"]
source = "172.28.10.100" if allow else "172.28.10.101"
assert any(event["source_ip"] == source and event["destination_port"] == 81
           and event["action"] == "BLOCK" for event in events)
stats = get_api("statistics")
assert stats["total"] == stats["allowed"] + stats["blocked"]
assert stats["allowed"] > 0 and stats["blocked"] > 0
print("PASS real blocked event and statistics through API")
