#!/usr/bin/env python3
"""Build the installable Anki add-on file.

Works on Windows, macOS and Linux – only Python is required, no extra tools.
Windows: double-click this file. Others: run ``python3 build.py``.

Result: dist/pronunciation_tts.ankiaddon
Install in Anki via Tools → Add-ons → Install from file…
"""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "pronunciation_tts"
OUT = ROOT / "dist" / "pronunciation_tts.ankiaddon"
SKIP_DIRS = {"__pycache__"}
SKIP_FILES = {"meta.json"}  # Anki's per-user state, must not be shipped
SKIP_SUFFIXES = {".pyc", ".pyo"}


def build(out: Path = OUT) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SRC.rglob("*")):
            rel = path.relative_to(SRC)
            if path.is_dir() or SKIP_DIRS & set(rel.parts):
                continue
            if path.name in SKIP_FILES or path.suffix in SKIP_SUFFIXES:
                continue
            # Files at the zip root (not inside a folder) – required by Anki.
            zf.write(path, rel.as_posix())
    return out


def main() -> None:
    out = build()
    print(f"Fertig / Done: {out}")
    print("Anki: Extras → Add-ons → Aus Datei installieren… / Tools → Add-ons → Install from file…")
    # Keep the window open when double-clicked on Windows.
    if os.name == "nt" and len(sys.argv) == 1 and sys.stdin and sys.stdin.isatty():
        input("\nEnter drücken zum Schließen / Press Enter to close …")


if __name__ == "__main__":
    main()
