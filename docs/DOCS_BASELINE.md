# FreeCAD Documentation Baseline

Date checked: 2026-05-22

This implementation is anchored to the current FreeCAD and Orville references below:

- FreeCAD latest release page: https://github.com/FreeCAD/FreeCAD
- FreeCAD developer dependency guidance: https://freecad.github.io/DevelopersHandbook/gettingstarted/dependencies.html
- FreeCAD workbench creation: https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/Workbench_creation.md
- FreeCAD package metadata: https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/Package_Metadata.md
- FreeCAD Addon Manager: https://github.com/FreeCAD/AddonManager
- FreeCAD standard import command: https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/Std_Import.md
- FreeCAD official Addon Template package metadata example: https://raw.githubusercontent.com/FreeCAD/Addon-Template/main/package.xml
- Orville CAD API docs: https://www.ballistalabs.ai/docs/api
- Orville OpenAPI JSON: https://www.ballistalabs.ai/api/v1/openapi.json

Key implementation choices from those sources:

- The workbench is a Python-only external addon.
- FreeCAD discovers the addon through top-level `Init.py` and `InitGui.py`.
- GUI code is loaded from `InitGui.py` and command activation, not from `Init.py`.
- Qt imports use FreeCAD's `PySide` compatibility module.
- Addon Manager metadata lives in `package.xml` format 1.
- STEP files are imported through FreeCAD's import stack rather than parsed by this addon.
- The public OpenAPI schema checked on 2026-05-22 is version `2026-05-21`. It exposes recent CAD job listing with `GET /api/v1/cad/jobs`, public message history with `GET /api/v1/cad/jobs/{jobId}/messages`, and `poll_after_seconds` as the recommended delay before the next poll.
- The public OpenAPI schema does not expose a distinct review endpoint or message mode field, so review UX currently routes through the same job message prompt path.
