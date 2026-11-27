
# ---- common.sh: eseguito su tutti gli host (variabili esportate dall'intestazione) ----
set -eu -o pipefail
export DEBIAN_FRONTEND=noninteractive
APT="apt-get -o Acquire::Retries=5 -y -qq"

mkdir -p /opt/aizoon
chmod 700 /opt/aizoon

$APT update
$APT install curl gnupg ca-certificates python3-boto3

# CloudWatch agent: metriche memoria/disco e syslog.
curl -fsSL -o /opt/aizoon/amazon-cloudwatch-agent.deb \
  https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i /opt/aizoon/amazon-cloudwatch-agent.deb

cat > /opt/aws/amazon-cloudwatch-agent/etc/aizoon.json <<'EOF'
{
  "agent": {"metrics_collection_interval": 60, "region": "LAB_REGION"},
  "metrics": {
    "namespace": "AizoonLab",
    "append_dimensions": {"InstanceId": "${aws:InstanceId}"},
    "metrics_collected": {
      "mem": {"measurement": ["mem_used_percent"]},
      "disk": {"measurement": ["used_percent"], "resources": ["/"], "drop_device": true}
    }
  },
  "logs": {"logs_collected": {"files": {"collect_list": [
    {"file_path": "/var/log/syslog", "log_group_name": "/LAB_PROJECT/system", "log_stream_name": "{instance_id}/syslog"}
  ]}}}
}
EOF
sed -i "s#LAB_REGION#${REGION}#; s#LAB_PROJECT#${PROJECT}#" /opt/aws/amazon-cloudwatch-agent/etc/aizoon.json
chmod 600 /opt/aws/amazon-cloudwatch-agent/etc/aizoon.json
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/aizoon.json -s
