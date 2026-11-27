
# ---- waf-health.sh: metrica HTTPSAvailable ogni minuto (solo WAF) ----
cat > /opt/aizoon/https-health.py <<'EOF'
import os
import ssl
import urllib.request

import boto3

available = 0
try:
    context = ssl.create_default_context(cafile='/opt/aizoon/tls/lab-ca.crt')
    with urllib.request.urlopen('https://' + os.environ['WAF_PUBLIC'] + '/', context=context, timeout=10) as response:
        available = int(response.status == 200 and b'Juice Shop' in response.read(4096))
except Exception as error:
    print(type(error).__name__)
boto3.client('cloudwatch', region_name=os.environ['REGION']).put_metric_data(
    Namespace='AizoonLab', MetricData=[{
        'MetricName': 'HTTPSAvailable', 'Value': available, 'Unit': 'Count',
        'Dimensions': [{'Name': 'Project', 'Value': os.environ['PROJECT']}]
    }])
print('HTTPSAvailable=' + str(available))
EOF
chmod 700 /opt/aizoon/https-health.py

cat > /opt/aizoon/health.env <<EOF
WAF_PUBLIC=${WAF_PUBLIC}
REGION=${REGION}
PROJECT=${PROJECT}
EOF
chmod 600 /opt/aizoon/health.env

cat > /etc/systemd/system/aizoon-health.service <<'EOF'
[Unit]
Description=Aizoon HTTPS health metric
After=network-online.target docker.service
[Service]
Type=oneshot
EnvironmentFile=/opt/aizoon/health.env
ExecStart=/usr/bin/python3 /opt/aizoon/https-health.py
EOF

cat > /etc/systemd/system/aizoon-health.timer <<'EOF'
[Unit]
Description=Check Aizoon HTTPS every minute
[Timer]
OnBootSec=60
OnUnitActiveSec=60
[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now aizoon-health.timer
