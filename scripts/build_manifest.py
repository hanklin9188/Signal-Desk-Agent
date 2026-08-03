from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "AppPackages",
    "bin",
    "build",
    "data",
    "dist",
    "obj",
    "outputs",
    "runs",
    "service",
}
EXCLUDED_FILES = {
    ".auth-token",
    ".env",
    "MANIFEST.json",
    "credentials.json",
    "token.json",
}
EXCLUDED_SUFFIXES = {".appx", ".appxbundle", ".cer", ".db", ".msix", ".msixbundle", ".p12", ".pfx"}


def main() -> None:
    entries = []
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or path.name in EXCLUDED_FILES
            or path.suffix.lower() in EXCLUDED_SUFFIXES
        ):
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        content = path.read_bytes()
        entries.append(
            {
                "path": relative.as_posix(),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    (ROOT / "MANIFEST.json").write_text(
        json.dumps({"files": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
