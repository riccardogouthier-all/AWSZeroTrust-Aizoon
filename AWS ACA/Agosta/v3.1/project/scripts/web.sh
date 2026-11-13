
# ---- web.sh: Juice Shop privato su :3000 ----
$APT install docker.io
systemctl enable --now docker

if ! docker inspect juice-shop >/dev/null 2>&1; then
  docker pull "$JUICE_IMAGE"
  docker run -d --name juice-shop --restart unless-stopped \
    --log-opt max-size=10m --log-opt max-file=3 \
    -p 3000:3000 "$JUICE_IMAGE"
fi

for _ in $(seq 1 30); do
  curl -fs -o /dev/null http://127.0.0.1:3000/ && break
  sleep 5
done
curl -fs -o /dev/null http://127.0.0.1:3000/
