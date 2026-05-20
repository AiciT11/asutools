"""Build asuTools.dmg from the installed .app bundle.

Uses macOS-native `hdiutil` only. Layout:
  - asuTools.app
  - Applications  (symlink to /Applications, so user can drag-install)
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "asuTools"
VERSION = "0.1.0"

DIST_DIR = PROJECT_DIR / "dist"
DMG_PATH = DIST_DIR / f"{APP_NAME}-{VERSION}.dmg"


def _ensure_app(app_path: Path) -> None:
    if not app_path.exists():
        raise SystemExit(f"找不到 {app_path}。先跑 scripts/make_app.py")


def build_dmg(app_path: Path) -> Path:
    _ensure_app(app_path)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if DMG_PATH.exists():
        DMG_PATH.unlink()

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "stage"
        staging.mkdir()

        # Copy the .app — must preserve symlinks/perms (use cp -R)
        subprocess.run(["cp", "-R", str(app_path), str(staging)], check=True)
        # /Applications symlink for drag-install affordance
        (staging / "Applications").symlink_to("/Applications")

        subprocess.run(
            [
                "hdiutil", "create",
                "-volname", f"{APP_NAME} {VERSION}",
                "-srcfolder", str(staging),
                "-ov", "-format", "UDZO",
                str(DMG_PATH),
            ],
            check=True,
        )

    return DMG_PATH


def main() -> None:
    # Prefer PyInstaller output (self-contained, ~80MB), fall back to installed copies.
    candidates = [
        DIST_DIR / f"{APP_NAME}.app",
        Path.home() / "Applications" / f"{APP_NAME}.app",
        Path("/Applications") / f"{APP_NAME}.app",
    ]
    app_path = next((p for p in candidates if p.exists()), None)
    if app_path is None:
        raise SystemExit(
            "找不到 asuTools.app。先跑 scripts/make_app.py 或 scripts/build_release.py"
        )
    print(f"打包来源: {app_path}")
    out = build_dmg(app_path)
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"wrote: {out}  ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
