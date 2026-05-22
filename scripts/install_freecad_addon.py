"""Agent-friendly installer for the Orville FreeCAD addon.

Prefer running this with FreeCAD's Python or FreeCADCmd so it can use the
Addon Manager installer API. If that API is unavailable, it falls back to a
plain git clone/update in the user's FreeCAD Mod directory.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET


REPO_URL = "https://github.com/Genesis-engi/orville-freecad-plugin.git"
ZIP_URL = "https://github.com/Genesis-engi/orville-freecad-plugin/archive/refs/heads/main.zip"
BRANCH = "main"
ADDON_DIR_NAME = "orville-freecad-plugin"


class _Metadata:
    def __init__(self, version: str = ""):
        self.version = version


class _OrvilleAddon:
    name = ADDON_DIR_NAME
    url = REPO_URL
    branch = BRANCH
    branch_display_name = BRANCH
    metadata = None
    installed_metadata = None
    icon_data = None

    def get_zip_url(self):
        return ZIP_URL

    def contains_workbench(self):
        return True

    def contains_preference_pack(self):
        return False

    def enable_workbench(self):
        return None

    def set_status(self, _status):
        return None

    def load_metadata_file(self, path):
        version = ""
        try:
            root = ET.parse(path).getroot()
            for child in root:
                if child.tag.endswith("version"):
                    version = child.text or ""
                    break
        except Exception:
            version = ""
        self.metadata = _Metadata(version)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or update the Orville FreeCAD addon.")
    parser.add_argument(
        "--method",
        choices=("auto", "addon-manager", "git"),
        default="auto",
        help="Install method. Default: auto.",
    )
    parser.add_argument(
        "--mod-dir",
        help="FreeCAD Mod directory. Optional when running under FreeCAD.",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Also try to install Python dependencies with this Python runtime.",
    )
    args = parser.parse_args()

    if args.install_deps:
        _install_dependencies()

    if args.method in ("auto", "addon-manager"):
        try:
            _install_with_addon_manager()
            print("Installed Orville through FreeCAD Addon Manager API.")
            print("Restart FreeCAD, then open the Orville workbench.")
            return 0
        except Exception as exc:
            if args.method == "addon-manager":
                print(f"Addon Manager install failed: {exc}", file=sys.stderr)
                return 1
            print(f"Addon Manager install unavailable, falling back to git: {exc}")

    mod_dir = Path(args.mod_dir).expanduser() if args.mod_dir else _default_mod_dir()
    _install_with_git(mod_dir)
    print(f"Installed Orville into {mod_dir / ADDON_DIR_NAME}")
    print("Restart FreeCAD, then open the Orville workbench.")
    return 0


def _install_with_addon_manager() -> None:
    from addonmanager_installer import AddonInstaller

    installer = AddonInstaller(_OrvilleAddon())
    if not installer.run():
        raise RuntimeError("AddonInstaller returned failure.")


def _install_with_git(mod_dir: Path) -> None:
    mod_dir.mkdir(parents=True, exist_ok=True)
    target = mod_dir / ADDON_DIR_NAME

    if target.exists():
        if not (target / ".git").exists():
            raise RuntimeError(f"{target} already exists and is not a git checkout.")
        _run(["git", "-C", str(target), "fetch", "origin", BRANCH])
        _run(["git", "-C", str(target), "checkout", BRANCH])
        _run(["git", "-C", str(target), "pull", "--ff-only", "origin", BRANCH])
        return

    _run(["git", "clone", "--branch", BRANCH, "--depth", "1", REPO_URL, str(target)])


def _install_dependencies() -> None:
    try:
        import keyring  # noqa: F401
        return
    except ImportError:
        pass

    try:
        _run([sys.executable, "-m", "pip", "install", "keyring"])
    except Exception as exc:
        print(f"Warning: could not install keyring automatically: {exc}", file=sys.stderr)
        print("Orville can still run with a session-only API key fallback.", file=sys.stderr)


def _default_mod_dir() -> Path:
    try:
        import FreeCAD

        return Path(FreeCAD.getUserAppDataDir()) / "Mod"
    except ImportError:
        pass

    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA is not set. Pass --mod-dir explicitly.")
        return Path(appdata) / "FreeCAD" / "v1-1" / "Mod"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "FreeCAD" / "Mod"
    return Path.home() / ".local" / "share" / "FreeCAD" / "Mod"


def _run(command: list[str]) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
