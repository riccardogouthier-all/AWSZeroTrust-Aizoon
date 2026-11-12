"""Save current Terraform outputs without PowerShell encoding differences."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if __name__ == "__main__":
    result = subprocess.run(["terraform", f"-chdir={ROOT / 'terraform'}", "output", "-json"], check=True, capture_output=True, text=True)
    json.loads(result.stdout)
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "outputs.json").write_text(result.stdout, encoding="utf-8")
    print("Updated local evidence/outputs.json")
