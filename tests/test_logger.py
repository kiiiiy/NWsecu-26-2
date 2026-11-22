import importlib.util
from pathlib import Path
import socket
import struct
import unittest

spec = importlib.util.spec_from_file_location("logger", Path(__file__).parents[1] / "firewall" / "logger.py")
logger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logger)


def attribute(kind, payload):
    data = struct.pack("=HH", len(payload) + 4, kind) + payload
    return data + b"\0" * (-len(data) % 4)


def packet(proto=6, fragment=0, options=b"", port=80):
    ip = struct.pack("!BBHHHBBH4s4s", 0x45 + len(options) // 4, 0, 24 + len(options),
                     0, fragment, 64, proto, 0, socket.inet_aton("192.168.0.25"),
                     socket.inet_aton("172.28.20.10"))
    return ip + options + struct.pack("!HH", 43210, port)


class LogDecoderTests(unittest.TestCase):
    def test_tcp_allow(self):
        event = logger.decode(attribute(10, b"ALLOW\0") + attribute(9, packet()))
        self.assertEqual((event["action"], event["src_ip"], event["dst_port"], event["protocol"]),
                         ("ALLOW", "192.168.0.25", 80, "TCP"))

    def test_udp_block_with_ip_options(self):
        event = logger.decode(attribute(9, packet(proto=17, options=b"\0" * 4, port=53)) + attribute(10, b"BLOCK\0"))
        self.assertEqual((event["action"], event["dst_port"], event["protocol"]), ("BLOCK", 53, "UDP"))

    def test_icmp_and_noninitial_fragment_have_no_port(self):
        for data in (packet(proto=1), packet(fragment=1)):
            self.assertIsNone(logger.decode(attribute(9, data))["dst_port"])

    def test_missing_or_truncated_payload(self):
        for data in (b"", attribute(9, b"\x45"), struct.pack("=HH", 200, 9) + b"\x45"):
            self.assertIsNone(logger.decode(data))

    def test_multiple_events_in_one_receive(self):
        messages = []
        for action in (b"ALLOW\0", b"BLOCK\0"):
            body = struct.pack("!BBH", socket.AF_INET, 0, logger.NFLOG_GROUP)
            body += attribute(logger.ATTR_PREFIX, action) + attribute(logger.ATTR_PAYLOAD, packet())
            message = struct.pack("=IHHII", 16 + len(body), logger.NFLOG_PACKET, 0, 0, 0) + body
            messages.append(message + b"\0" * (-len(message) % 4))
        events = list(logger.read_events(b"".join(messages)))
        self.assertEqual([event["action"] for event in events], ["ALLOW", "BLOCK"])

    def test_truncated_netlink_message_is_rejected(self):
        header = struct.pack("=IHHII", 100, logger.NFLOG_PACKET, 0, 0, 0)
        with self.assertRaises(RuntimeError):
            list(logger.read_events(header))


if __name__ == "__main__":
    unittest.main()
