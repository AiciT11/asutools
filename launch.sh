#!/bin/bash
# asuTools 启动脚本
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/.venv/bin/python" -m asutools "$@"
