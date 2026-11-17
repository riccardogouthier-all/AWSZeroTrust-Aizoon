"""Verifica un albero di pubblicazione prima del rilascio. Non stampa contenuti."""
import argparse
from pathlib import Path

PRIVATE_SUFFIXES = {
    ".bak": "forgottenDevBackupChallenge / forgottenBackupChallenge",
    ".log": "accessLogDisclosureChallenge",
    ".tf": "misplacedIacFiles",
    ".tfvars": "misplacedIacFiles",
    ".tfstate": "misplacedIacFiles",
}


def findings(root):
    if not root.is_dir() or not any(root.iterdir()):
        raise ValueError("Specificare una directory di pubblicazione popolata")
    for file in sorted(root.rglob("*")):
        relative = file.relative_to(root)
        parts = [part.lower() for part in relative.parts]
        if file.is_symlink():
            yield relative, "lfrChallenge: verificare il target fuori dalla release"
        elif file.is_file():
            if parts[0] == "ftp" and relative.as_posix() != "ftp/legal.md":
                yield relative, "directoryListingChallenge: file fuori allowlist FTP"
            suffix = file.suffix.lower()
            if suffix in PRIVATE_SUFFIXES:
                yield relative, PRIVATE_SUFFIXES[suffix]
            if parts[-1] in {"dockerfile", "docker-compose.yml", "compose.yaml", "compose.yml", ".terraform.lock.hcl"}:
                yield relative, "misplacedIacFiles"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("webroot", type=Path)
    issues = list(findings(parser.parse_args().webroot))
    for path, challenge in issues:
        print(f"{challenge} | {path}")
    print(f"Rilievi: {len(issues)}")
    raise SystemExit(int(bool(issues)))
