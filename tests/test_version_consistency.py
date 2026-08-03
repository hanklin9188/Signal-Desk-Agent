from __future__ import annotations

import re
import tomllib
from pathlib import Path

from signaldesk import __version__


def test_python_package_and_msix_versions_match() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = (root / "native/SignalDesk.Shell/Package.appxmanifest").read_text(
        encoding="utf-8"
    )
    package_version = project["project"]["version"]
    manifest_version = re.search(r'\bVersion="([0-9.]+)"', manifest)

    assert manifest_version is not None
    assert __version__ == package_version == manifest_version.group(1)
