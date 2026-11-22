"""Run after integration clients to verify actual kernel audit events."""
import json
import datetime
import sys
from pathlib import Path

events = [json.loads(line) for line in (Path(__file__).parents[1] / "logs" / "firewall.log").read_text().splitlines() if line.strip()]
# 과거에 성공한 기록으로 이번 검사가 통과하지 않도록 시작 시각 이후만 확인한다.
if len(sys.argv) > 1:
    started_at = datetime.datetime.fromisoformat(sys.argv[1])
    events = [event for event in events if datetime.datetime.fromisoformat(event["timestamp"]) >= started_at]
required = {
    ("172.28.10.100", 80, "ALLOW"),
    ("172.28.10.100", 22, "ALLOW"),
    ("172.28.10.100", 81, "BLOCK"),
    ("172.28.10.101", 80, "ALLOW"),
    ("172.28.10.101", 22, "BLOCK"),
    ("172.28.10.101", 81, "BLOCK"),
}
actual = {(e["src_ip"], e["dst_port"], e["action"]) for e in events}
missing = required - actual
assert not missing, f"Missing real firewall events: {missing}"
assert not any(e["src_ip"] == "172.28.10.101" and e["dst_port"] == 22 and e["action"] == "ALLOW" for e in events)
print("PASS real firewall.log: source IP, destination port, ALLOW/BLOCK (6 cases)")
