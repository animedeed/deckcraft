"""Read-only dependency diagnostics for a local Deckcraft executor."""
from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys

REQUIRED = {"python-pptx": "pptx", "lxml": "lxml", "Pillow": "PIL", "numpy": "numpy", "shapely": "shapely"}


def inspect() -> dict:
    packages = {}
    for distribution, module in REQUIRED.items():
        try:
            importlib.import_module(module)
            packages[distribution] = {"ok": True, "version": importlib.metadata.version(distribution)}
        except (ImportError, OSError) as exc:
            packages[distribution] = {"ok": False, "error": str(exc)}
    schema_dir = os.environ.get("DECKCRAFT_XSD_DIR")
    schema = Path(schema_dir) / "pml.xsd" if schema_dir else None
    browser = os.environ.get("DECKCRAFT_CHROME")
    optional = {"soffice": os.environ.get("DECKCRAFT_SOFFICE") or shutil.which("soffice"),
                "pdftoppm": os.environ.get("DECKCRAFT_PDFTOPPM") or shutil.which("pdftoppm"),
                "browser": browser if browser and Path(browser).is_file() else None,
                "xsd": "available" if schema and schema.is_file() else "invalid path" if schema else "not configured"}
    ok = sys.version_info >= (3, 10) and all(item["ok"] for item in packages.values())
    return {"ok": ok, "python": sys.executable, "python_version": sys.version.split()[0],
            "packages": packages, "optional": optional,
            "next_step": None if ok else "Use a compatible Python 3.10+ virtual environment and install requirements.txt there."}


if __name__ == "__main__":
    report = inspect()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["ok"] else 1)
