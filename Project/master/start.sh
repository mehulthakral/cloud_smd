#!/bin/sh

echo "starting python3 -u /app/main.py"
python3 -u /app/main.py &

exec /usr/local/bin/docker-entrypoint.sh "$@"
