import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_build():
    spec = importlib.util.spec_from_file_location("build_addon", ROOT / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_creates_installable_zip(tmp_path):
    build = _load_build()
    # simulate junk that must not be shipped
    junk = ROOT / "pronunciation_tts" / "__pycache__" / "junk.pyc"
    junk.parent.mkdir(exist_ok=True)
    junk.write_bytes(b"x")
    out = build.build(tmp_path / "x.ankiaddon")
    names = zipfile.ZipFile(out).namelist()
    for required in ("__init__.py", "manifest.json", "config.json", "config.md", "net.py", "icons/speaker.svg", "LICENSE"):
        assert required in names
    assert not any("__pycache__" in n or n.endswith(".pyc") or n == "meta.json" for n in names)
    assert not any(n.startswith("pronunciation_tts/") for n in names)  # files must be at zip root
