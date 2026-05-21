"""FreeCAD STEP import adapter."""

from __future__ import annotations

import os


class StepImportError(RuntimeError):
    pass


def import_step_file(path: str) -> None:
    if not path or not os.path.exists(path):
        raise StepImportError(f"STEP file does not exist: {path}")

    if not path.lower().endswith((".step", ".stp")):
        raise StepImportError(f"Not a STEP file: {path}")

    try:
        import FreeCAD as App
        import FreeCADGui as Gui
        import ImportGui
    except Exception as exc:  # pragma: no cover - requires FreeCAD runtime
        raise StepImportError("STEP import requires FreeCAD GUI mode.") from exc

    document = App.ActiveDocument
    if document is None:
        raise StepImportError("Open or create a FreeCAD document before importing.")

    ImportGui.insert(path, document.Name)
    document.recompute()

    try:
        Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass
