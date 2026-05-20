"""Build a self-contained release: PyInstaller .app + .dmg.

Output:
    dist/asuTools.app             ~80MB, fully self-contained
    dist/asuTools-<version>.dmg   draggable installer with /Applications symlink

PyInstaller bundles Python + PyQt6 inside the .app so the executable lives at
.app/Contents/MacOS/asuTools and macOS can resolve the bundle correctly:
Dock label and ⌘Tab show "asuTools" (not "python3").

Usage:
    uv run python scripts/build_release.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP = DIST / "asuTools.app"


def run(cmd, **kw):
    print(f"$ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main() -> None:
    # Clean previous build artifacts (keep any .dmg around — make_dmg replaces it).
    for p in (BUILD, APP, ROOT / "asuTools.spec"):
        if p.is_dir():
            shutil.rmtree(p)
        elif p.is_file():
            p.unlink()

    pyinstaller_cmd = [
        "uv", "run", "pyinstaller",
        "--noconfirm",
        "--windowed",
        "--name", "asuTools",
        "--icon", str(ROOT / "asutools" / "resources" / "icon.icns"),
        "--osx-bundle-identifier", "com.asu.asutools",
        "--add-data", f"{ROOT / 'asutools' / 'resources' / 'icon.png'}:asutools/resources",
        "--add-data", f"{ROOT / 'asutools' / 'resources' / 'icon.icns'}:asutools/resources",
        "--hidden-import", "asutools.ui.main_window",
        "--hidden-import", "asutools.ui.tabs",
        "--hidden-import", "asutools.ui.grid",
        "--hidden-import", "asutools.ui.dialogs",
        "--hidden-import", "setproctitle",
        "--hidden-import", "Foundation",
        "--hidden-import", "AppKit",
        "--collect-submodules", "asutools",
        str(ROOT / "scripts" / "run_asutools.py"),
    ]
    run(pyinstaller_cmd, cwd=ROOT)

    if not APP.exists():
        sys.exit("PyInstaller didn't produce dist/asuTools.app")

    size_mb = sum(p.stat().st_size for p in APP.rglob("*") if p.is_file()) / (1024 ** 2)
    print(f"\n✓ {APP}  ({size_mb:.1f} MB)")

    # Build the dmg from this .app
    run(["uv", "run", "python", str(ROOT / "scripts" / "make_dmg.py")], cwd=ROOT)


if __name__ == "__main__":
    main()
