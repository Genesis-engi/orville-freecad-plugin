# Orville FreeCAD Plugin

Open-source FreeCAD workbench for creating and iterating on CAD models through the Orville CAD API.

This repo is in early implementation. It includes a Python-only external FreeCAD workbench, a dockable Orville chat panel, image attachment validation, secure API key storage through `keyring`, Orville CAD API request handling, searchable recent job loading, review assistant messages, job polling, STEP download, and import into FreeCAD through FreeCAD's import stack.

## Install On Windows

For a typical Windows setup experience, download `Orville-FreeCAD-Setup.exe` from the latest GitHub release and run the installer.

The installer:

- installs Orville into the current user's FreeCAD addon directory,
- does not require administrator rights,
- can check/install the `keyring` dependency through FreeCAD's Python,
- can launch FreeCAD after setup.

After restart, switch to the `Orville` workbench and click `Open Orville`.

On first launch, Orville prompts for an API key before enabling the normal interface. The key is stored in secure OS storage when available. To replace or clear the key later, use the `Settings` button in the Orville panel header.

Use `New Chat` to start a fresh CAD job after a result comes back. The `Recent Jobs` list loads recent workspace jobs from the Orville API; double-click a job to restore its public chat history and latest STEP artifacts. `Review` sends a synchronous review assistant request against the completed job; `Iterate` sends a CAD follow-up.

## Install With Addon Manager

This addon is not yet in the central FreeCAD addon catalog. Add it as a custom repository:

1. Open FreeCAD.
2. Go to `Edit > Preferences > Addon Manager > Addon Manager Options`.
3. Add a custom repository:
   - Repository URL: `https://github.com/Genesis-engi/orville-freecad-plugin.git`
   - Branch: `main`
4. Open `Tools > Addon Manager`.
5. Refresh the addon list if needed.
6. Select `Orville` and install it.
7. Restart FreeCAD.

If prompted to install the Python dependency `keyring`, accept it. Orville uses it for secure API key storage.

## Agent-Assisted Install

An automation agent can install or update Orville without clicking through the UI. From a local checkout of this repo, run the helper script with FreeCAD's Python runtime:

```bash
FreeCADCmd scripts/install_freecad_addon.py --install-deps
```

The script first tries FreeCAD's Addon Manager Python API. If that API is unavailable, it falls back to cloning this repository into the user's FreeCAD `Mod` directory. It does not accept or store an API key; first launch still prompts for that inside Orville.

## Manual Install Fallback

If Addon Manager cannot install from the custom repository, clone or copy this folder into your FreeCAD user `Mod` directory, then restart FreeCAD.

- Windows FreeCAD 1.1: `%APPDATA%\FreeCAD\v1-1\Mod\orville-freecad-plugin`
- Older Windows FreeCAD installs: `%APPDATA%\FreeCAD\Mod\orville-freecad-plugin`
- macOS: `~/Library/Application Support/FreeCAD/Mod/orville-freecad-plugin`
- Linux: `~/.local/share/FreeCAD/Mod/orville-freecad-plugin`

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
