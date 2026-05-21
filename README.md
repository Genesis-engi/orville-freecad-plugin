# Orville FreeCAD Plugin

Open-source FreeCAD workbench for creating and iterating on CAD models through the Orville CAD API.

This repo is in early implementation. It includes a Python-only external FreeCAD workbench, a dockable Orville chat panel, image attachment validation, secure API key storage through `keyring`, Orville CAD API request handling, job polling, STEP download, and import into the active FreeCAD document through FreeCAD's import stack.

## Manual Install

Clone or copy this folder into your FreeCAD user `Mod` directory, then restart FreeCAD.

- Windows: `%APPDATA%\FreeCAD\Mod\orville-freecad-plugin`
- macOS: `~/Library/Application Support/FreeCAD/Mod/orville-freecad-plugin`
- Linux: `~/.local/share/FreeCAD/Mod/orville-freecad-plugin`

Install the Python `keyring` package into FreeCAD's Python environment if Addon Manager does not install it automatically. You can also set `ORVILLE_API_KEY` for a session without storing the key.

After restart, switch to the `Orville` workbench and click `Open Orville`.

## Development

Run the normal-Python tests from the repo root:

```bash
python -m unittest discover -s tests -v
python -m compileall -q orville_freecad Init.py InitGui.py
```

## Planning Baseline

The working plan is in [PLAN.md](PLAN.md). The documentation baseline is in [docs/DOCS_BASELINE.md](docs/DOCS_BASELINE.md).

## License

MIT. If this workbench is ever proposed for inclusion inside FreeCAD itself, the license may need to be revisited because FreeCAD core integration expects LGPL-compatible licensing.
