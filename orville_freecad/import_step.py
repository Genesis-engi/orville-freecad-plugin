"""FreeCAD STEP import adapter."""

from __future__ import annotations

import os
import re


class StepImportError(RuntimeError):
    pass


def import_step_file(path: str) -> None:
    _validate_step_path(path)

    try:
        import FreeCAD as App
        import FreeCADGui as Gui
        import ImportGui
    except Exception as exc:  # pragma: no cover - requires FreeCAD runtime
        raise StepImportError("STEP import requires FreeCAD GUI mode.") from exc

    document = App.ActiveDocument
    if document is None:
        raise StepImportError("Open or create a FreeCAD document before importing.")

    _insert_step(path, document)
    _fit_view(Gui)


def import_step_file_to_new_document(path: str, document_name: str | None = None) -> str:
    _validate_step_path(path)

    try:
        import FreeCAD as App
        import FreeCADGui as Gui
        import ImportGui
    except Exception as exc:  # pragma: no cover - requires FreeCAD runtime
        raise StepImportError("STEP import requires FreeCAD GUI mode.") from exc

    raw_document_name = os.path.splitext(document_name or os.path.basename(path))[0]
    document = App.newDocument(safe_document_name(raw_document_name))
    try:
        Gui.ActiveDocument = Gui.getDocument(document.Name)
    except Exception:
        pass

    _insert_step(path, document)
    _fit_view(Gui)
    return document.Name


def safe_document_name(value: str) -> str:
    name = re.sub(r"\W+", "_", value or "Orville_Result").strip("_")
    if not name:
        name = "Orville_Result"
    if name[0].isdigit():
        name = f"Orville_{name}"
    return name[:80]


def _validate_step_path(path: str) -> None:
    if not path or not os.path.exists(path):
        raise StepImportError(f"STEP file does not exist: {path}")

    if not path.lower().endswith((".step", ".stp")):
        raise StepImportError(f"Not a STEP file: {path}")


def _insert_step(path, document) -> None:
    import ImportGui
    ImportGui.insert(path, document.Name)
    document.recompute()


def _fit_view(gui) -> None:
    try:
        gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass
