"""Filesystem paths for local Orville artifacts."""

from __future__ import annotations

from pathlib import Path


def artifact_cache_dir() -> str:
    try:
        import FreeCAD as App

        root = Path(App.getUserAppDataDir())
    except Exception:
        root = Path.home() / ".cache" / "freecad"

    path = root / "Orville" / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)
