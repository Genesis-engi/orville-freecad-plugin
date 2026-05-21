"""FreeCAD command registration for the Orville workbench."""

from __future__ import annotations

import os

import FreeCADGui as Gui

from . import metadata


COMMANDS = [metadata.COMMAND_OPEN_PANEL]
_registered = False


class OpenPanelCommand:
    def GetResources(self):
        icon = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "orville.png")
        return {
            "Pixmap": icon,
            "MenuText": "Open Orville",
            "ToolTip": "Open the Orville CAD generation panel",
        }

    def Activated(self):
        from .ui.panel import show_panel

        show_panel()

    def IsActive(self):
        return True


def register_commands() -> None:
    global _registered
    if _registered:
        return

    Gui.addCommand(metadata.COMMAND_OPEN_PANEL, OpenPanelCommand())
    _registered = True
