# Orville FreeCAD Plugin

Open-source FreeCAD workbench for creating and iterating on CAD models through the Orville CAD API.

This repo is in early implementation. It includes a Python-only external FreeCAD workbench, a dockable Orville chat panel, image attachment validation, secure API key storage through `keyring`, Orville CAD API request handling, searchable recent job loading, review assistant messages, job polling, STEP download, and import into FreeCAD through FreeCAD's import stack.

## Manual Install

Clone or copy this folder into your FreeCAD user `Mod` directory, then restart FreeCAD.

- Windows FreeCAD 1.1: `%APPDATA%\FreeCAD\v1-1\Mod\orville-freecad-plugin`
- Older Windows FreeCAD installs: `%APPDATA%\FreeCAD\Mod\orville-freecad-plugin`
- macOS: `~/Library/Application Support/FreeCAD/Mod/orville-freecad-plugin`
- Linux: `~/.local/share/FreeCAD/Mod/orville-freecad-plugin`

After restart, switch to the `Orville` workbench and click `Open Orville`.

On first launch, Orville prompts for an API key before enabling the normal interface. The key is stored in secure OS storage when available. To replace or clear the key later, use the `Settings` button in the Orville panel header.

Use `New Chat` to start a fresh CAD job after a result comes back. The `Recent Jobs` list loads recent workspace jobs from the Orville API; double-click a job to restore its public chat history and latest STEP artifacts. `Review` sends a synchronous review assistant request against the completed job; `Iterate` sends a CAD follow-up.

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
