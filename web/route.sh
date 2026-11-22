#!/bin/sh
set -eu
ip route replace default via 172.28.20.2
