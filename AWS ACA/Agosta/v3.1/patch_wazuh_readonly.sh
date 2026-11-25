#!/usr/bin/env bash
set -euo pipefail

# Wazuh 4.14.10: selecting a data source needs fresh fields in memory only.
python3 - <<'PY'
from pathlib import Path
import gzip
import os
import shutil
import subprocess
import tempfile

root = Path("/usr/share/wazuh-dashboard")
chunk = root / "plugins/wazuh/target/public/wazuh.chunk.2.js"
old = chunk.read_bytes()
before = b"pattern.fields.replaceAll([...fields,...scripted]);await this.patternService.updateSavedObject(pattern)}catch{}}else{throw new Error(\"Error selecting index pattern: pattern not found\")}"
after = before.replace(b";await this.patternService.updateSavedObject(pattern)", b"")
if old.count(after) == 1 and before not in old:
    print("Wazuh data-source patch already installed")
    raise SystemExit
if old.count(before) != 1 or subprocess.check_output(["dpkg-query", "-W", "-f=${Version}", "wazuh-dashboard"]).decode().split("-", 1)[0] != "4.14.10":
    raise SystemExit("Unsupported Wazuh Dashboard build")

new = old.replace(before, after, 1)
node = root / "node/bin/node"
subprocess.run([node, "--check", "-"], input=new, check=True)
brotli = subprocess.check_output(
    [node, "-e", "const fs=require('fs'); const z=require('zlib'); process.stdout.write(z.brotliCompressSync(fs.readFileSync(0),{params:{[z.constants.BROTLI_PARAM_QUALITY]:5}}));"],
    input=new,
)
variants = {chunk: new, Path(f"{chunk}.gz"): gzip.compress(new, mtime=0), Path(f"{chunk}.br"): brotli}
backup = Path(tempfile.mkdtemp(prefix="wazuh-readonly-", dir="/root"))
for path in variants:
    shutil.copy2(path, backup / path.name)
try:
    for path, data in variants.items():
        info = path.stat()
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
            temp.write(data)
            temp_path = Path(temp.name)
        os.chmod(temp_path, info.st_mode & 0o777)
        os.chown(temp_path, info.st_uid, info.st_gid)
        temp_path.replace(path)
except BaseException:
    for path in variants:
        shutil.copy2(backup / path.name, path)
    raise
print(f"Wazuh data-source patch installed. Backup: {backup}")
PY
