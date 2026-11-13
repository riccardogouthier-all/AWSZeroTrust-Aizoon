
# ---- waf.sh: nginx + ModSecurity + OWASP CRS, TLS con CA privata, modalita' DetectionOnly ----
$APT install docker.io openssl
systemctl enable --now docker

mkdir -p /opt/aizoon/tls
chmod 700 /opt/aizoon/tls
# Container nginx non privilegiato (uid 101) scrive qui.
mkdir -p /opt/aizoon/logs
chown 101:101 /opt/aizoon/logs
chmod 755 /opt/aizoon/logs

# CA privata + certificato per l'IP pubblico del WAF.
if [ ! -s /opt/aizoon/tls/server.crt ]; then
  (
    umask 077
    cd /opt/aizoon/tls
    openssl req -x509 -newkey rsa:3072 -nodes -days 30 \
      -keyout lab-ca.key -out lab-ca.crt -subj '/CN=Aizoon Private Learner Lab CA' \
      -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign'
    openssl req -new -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj "/CN=${WAF_PUBLIC}"
    printf 'subjectAltName=IP:%s\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "${WAF_PUBLIC}" > server.ext
    openssl x509 -req -in server.csr -CA lab-ca.crt -CAkey lab-ca.key -CAcreateserial \
      -out server.crt -days 30 -sha256 -extfile server.ext
    chmod 644 server.crt server.key lab-ca.crt
  )
fi

cat > /opt/aizoon/waf.env <<EOF
BACKEND=http://${WEB_PRIVATE}:3000
SERVER_NAME=${WAF_PUBLIC}
SSL_PORT=8443
MODSEC_RULE_ENGINE=DetectionOnly
MODSEC_AUDIT_ENGINE=RelevantOnly
MODSEC_AUDIT_LOG=/var/log/nginx/modsec_audit.log
MODSEC_AUDIT_LOG_FORMAT=JSON
ACCESSLOG=/var/log/nginx/access.log
ERRORLOG=/var/log/nginx/error.log
NGINX_X_FORWARDED_PORT=443
NGINX_X_FORWARDED_PROTO=https
EOF
chmod 600 /opt/aizoon/waf.env

cat > /opt/aizoon/start-waf.sh <<EOF
#!/bin/bash
set -euo pipefail
docker image inspect "${WAF_IMAGE}" >/dev/null 2>&1 || docker pull "${WAF_IMAGE}"
if ! docker inspect aizoon-waf >/dev/null 2>&1; then
  docker run -d --name aizoon-waf --restart unless-stopped \\
    --log-opt max-size=10m --log-opt max-file=3 \\
    --env-file /opt/aizoon/waf.env -p 443:8443 \\
    -v /opt/aizoon/tls/server.crt:/etc/nginx/conf/server.crt:ro \\
    -v /opt/aizoon/tls/server.key:/etc/nginx/conf/server.key:ro \\
    -v /opt/aizoon/logs:/var/log/nginx \\
    "${WAF_IMAGE}"
fi
EOF
chmod 700 /opt/aizoon/start-waf.sh

# Cambio modalita' esplicito: sudo /opt/aizoon/set-waf-mode.sh On|DetectionOnly
cat > /opt/aizoon/set-waf-mode.sh <<'EOF'
#!/bin/bash
set -euo pipefail
case "${1:-}" in On|DetectionOnly) ;; *) echo 'Use On or DetectionOnly' >&2; exit 2;; esac
sed -i "s/^MODSEC_RULE_ENGINE=.*/MODSEC_RULE_ENGINE=$1/" /opt/aizoon/waf.env
docker rm -f aizoon-waf
/opt/aizoon/start-waf.sh
EOF
chmod 700 /opt/aizoon/set-waf-mode.sh

/opt/aizoon/start-waf.sh
