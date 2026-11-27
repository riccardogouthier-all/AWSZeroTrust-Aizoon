#!/usr/bin/env bash
set -euo pipefail

# Selecting a data source needs fresh fields in memory only.
python3 - <<'PY'
from pathlib import Path
import gzip
import os
import re
import shutil
import subprocess
import tempfile

root = Path("/usr/share/wazuh-dashboard")
before = b"pattern.fields.replaceAll([...fields,...scripted]);await this.patternService.updateSavedObject(pattern)}catch{}}else{throw new Error(\"Error selecting index pattern: pattern not found\")}"
after = before.replace(b";await this.patternService.updateSavedObject(pattern)", b"")
version = subprocess.check_output(["dpkg-query", "-W", "-f=${Version}", "wazuh-dashboard"]).decode().split("-", 1)[0]
if version not in {"4.14.10", "4.14.11"}:
    raise SystemExit("Unsupported Wazuh Dashboard build")
matches = []
for chunk in (root / "plugins/wazuh/target/public").glob("wazuh*.js"):
    old = chunk.read_bytes()
    count = old.count(before) + old.count(after)
    if count:
        matches.append((chunk, old, count))
if len(matches) != 1 or matches[0][2] != 1:
    raise SystemExit("Wazuh data-source patch requires one exact bundle match")
chunk, old, _ = matches[0]

variants = {}
if before in old:
    new = old.replace(before, after, 1)
    node = root / "node/bin/node"
    subprocess.run([node, "--check", "-"], input=new, check=True)
    brotli = subprocess.check_output(
        [node, "-e", "const fs=require('fs'); const z=require('zlib'); process.stdout.write(z.brotliCompressSync(fs.readFileSync(0),{params:{[z.constants.BROTLI_PARAM_QUALITY]:5}}));"],
        input=new,
    )
    variants.update({chunk: new, Path(f"{chunk}.gz"): gzip.compress(new, mtime=0), Path(f"{chunk}.br"): brotli})
config = root / "data/wazuh/config/wazuh.yml"
settings = config.read_bytes()
key = rb"(?m)^checks\.fields[ \t]*:[^\r\n]*"
values = re.findall(key, settings)
if len(values) > 1 or (values and not re.fullmatch(rb"checks\.fields[ \t]*:[ \t]*(true|false)([ \t]+#.*|[ \t]*)", values[0])):
    raise SystemExit("Unsupported checks.fields setting")
updated = re.sub(rb"(?m)^(checks\.fields[ \t]*:[ \t]*)true\b", rb"\g<1>false", settings) if values else settings.rstrip(b"\r\n") + b"\nchecks.fields: false\n"
if updated != settings:
    variants[config] = updated
if not variants:
    print("Wazuh read-only patch already installed")
    raise SystemExit

backup = Path(tempfile.mkdtemp(prefix="wazuh-readonly-", dir="/root"))
for path in variants:
    shutil.copy2(path, backup / path.name)
service = ["systemctl", "restart", "wazuh-dashboard"]
restart = False
try:
    for path, data in variants.items():
        info = path.stat()
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
            temp.write(data)
            temp_path = Path(temp.name)
        os.chmod(temp_path, info.st_mode & 0o777)
        os.chown(temp_path, info.st_uid, info.st_gid)
        temp_path.replace(path)
    restart = True
    subprocess.run(service, check=True, timeout=45)
except BaseException:
    for path in variants:
        shutil.copy2(backup / path.name, path)
    if restart:
        subprocess.run(service, check=True, timeout=45)
    raise
print(f"Wazuh read-only patch installed. Backup: {backup}")
PY
