import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import socket
import struct

LOG_PATH = "/var/log/firewall/firewall.log"
NFLOG_GROUP = 10  # rules.sh의 --nflog-group과 같아야 한다.
NETLINK_NETFILTER = 12
NFLOG_PACKET = 0x400
NFLOG_CONFIG = 0x401
NETLINK_ACK = 2
REQUEST_WITH_ACK = 5
ATTR_PAYLOAD = 9
ATTR_PREFIX = 10
CONFIG_COMMAND = 1
CONFIG_MODE = 2
COMMAND_BIND = 1
COPY_PACKET = 2
NETLINK_HEADER_SIZE = 16
NFLOG_HEADER_SIZE = 4
PROTOCOL_NAMES = {6: "TCP", 17: "UDP", 1: "ICMP"}


def align4(size):
    return (size + 3) & ~3


def read_attributes(data):
    result = {}
    offset = 0
    while offset + 4 <= len(data):
        size, kind = struct.unpack_from("=HH", data, offset)
        if size < 4 or offset + size > len(data):
            break
        result[kind & 0x3FFF] = data[offset + 4:offset + size]
        offset += align4(size)
    return result


def decode(data):
    attributes = read_attributes(data)
    packet = attributes.get(ATTR_PAYLOAD, b"")
    if len(packet) < 20 or packet[0] >> 4 != 4:
        return None
    ip_header_size = (packet[0] & 15) * 4
    if ip_header_size < 20 or len(packet) < ip_header_size:
        return None
    protocol = packet[9]
    fragment_offset = struct.unpack_from("!H", packet, 6)[0] & 0x1FFF
    destination_port = None
    if protocol in (6, 17) and fragment_offset == 0 and len(packet) >= ip_header_size + 4:
        destination_port = struct.unpack_from("!H", packet, ip_header_size + 2)[0]
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "action": attributes.get(ATTR_PREFIX, b"UNKNOWN").rstrip(b"\0").decode("ascii", "replace"),
        "src_ip": socket.inet_ntoa(packet[12:16]),
        "dst_ip": socket.inet_ntoa(packet[16:20]),
        "dst_port": destination_port,
        "protocol": PROTOCOL_NAMES.get(protocol, str(protocol)),
    }


def send_config(sock, sequence, kind, payload):
    attribute = struct.pack("=HH", 4 + len(payload), kind) + payload
    attribute += b"\0" * (align4(len(attribute)) - len(attribute))
    body = struct.pack("!BBH", socket.AF_INET, 0, NFLOG_GROUP) + attribute
    header = struct.pack("=IHHII", NETLINK_HEADER_SIZE + len(body),
                         NFLOG_CONFIG, REQUEST_WITH_ACK, sequence, 0)
    sock.sendto(header + body, (0, 0))
    reply = sock.recv(65536)
    if len(reply) < 20 or struct.unpack_from("=H", reply, 4)[0] != NETLINK_ACK:
        raise RuntimeError("Unexpected netlink configuration reply")
    error = struct.unpack_from("=i", reply, 16)[0]
    if error:
        raise OSError(-error, os.strerror(-error))


def open_log():
    log = logging.getLogger("firewall")
    log.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    return log


def open_nflog():
    sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_NETFILTER)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    sock.bind((0, 0))
    send_config(sock, 1, CONFIG_COMMAND, bytes([COMMAND_BIND]))
    send_config(sock, 2, CONFIG_MODE, struct.pack("!IBB", 128, COPY_PACKET, 0))
    return sock


def read_events(data):
    offset = 0
    packet_start = NETLINK_HEADER_SIZE + NFLOG_HEADER_SIZE
    while offset + NETLINK_HEADER_SIZE <= len(data):
        size, kind = struct.unpack_from("=IH", data, offset)
        if size < NETLINK_HEADER_SIZE or offset + size > len(data):
            raise RuntimeError("Truncated netlink message")
        if kind == NFLOG_PACKET and size >= packet_start:
            event = decode(data[offset + packet_start:offset + size])
            if event:
                yield event
        offset += align4(size)


def main():
    log = open_log()
    with open_nflog() as sock:
        with open("/run/nflog.ready", "w"):
            pass
        while True:
            for event in read_events(sock.recv(262144)):
                log.info(json.dumps(event, separators=(",", ":")))


if __name__ == "__main__":
    main()
