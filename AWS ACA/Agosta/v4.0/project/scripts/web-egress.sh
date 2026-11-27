#!/usr/bin/env bash
set -euo pipefail

network=aizoon-web
bridge=br-aizoon-web
if ! docker network inspect "$network" >/dev/null 2>&1; then
    docker network create --driver bridge --opt "com.docker.network.bridge.name=$bridge" "$network" >/dev/null
fi
expected="bridge false $bridge"
actual=$(docker network inspect --format '{{.Driver}} {{.EnableIPv6}} {{index .Options "com.docker.network.bridge.name"}}' "$network")
[[ "$actual" == "$expected" ]]

# Leave replies to incoming connections available. Deny new forwarded and host-bound traffic.
rule=(-i "$bridge" -m conntrack '!' --ctstate ESTABLISHED,RELATED -j REJECT)
for chain in DOCKER-USER INPUT; do
    if ! iptables -w 5 -C "$chain" "${rule[@]}" 2>/dev/null; then
        iptables -w 5 -I "$chain" 1 "${rule[@]}"
    fi
done
