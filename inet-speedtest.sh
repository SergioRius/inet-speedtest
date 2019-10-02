#!/bin/bash

docker build -t inet-speedtest .
docker rm -f inet-speedtest
docker run --name inet-speedtest --restart=unless-stopped \
  -e DELAY=1800 \
  -e INFLUXDB_HOST=influxdb \
  -e INFLUXDB_DATABASE=network \
  -e INFLUXDB_MEASUREMENT=wan_speed \
  -e TZ="Europe/Madrid" \
  --network="monitoring" \
  -d inet-speedtest

