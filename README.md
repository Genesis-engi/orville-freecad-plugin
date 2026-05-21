# Orville FreeCAD Plugin

Open-source FreeCAD workbench for creating and iterating on CAD models through the Orville CAD API.

This repo is currently in planning/bootstrap state. The target implementation is a Python-only external FreeCAD workbench with a chat-style UI, image attachments, secure API key storage, job polling, STEP download, and import into the active FreeCAD document through FreeCAD's standard import path.

## Planning Baseline

The working plan is in [PLAN.md](PLAN.md). It is anchored to FreeCAD's current workbench/addon documentation and the Orville CAD API contract.

## License

MIT. If this workbench is ever proposed for inclusion inside FreeCAD itself, the license may need to be revisited because FreeCAD core integration expects LGPL-compatible licensing.
