"""FreeCAD GUI registration for the Orville workbench."""

import os
import sys

import FreeCAD as App
import FreeCADGui as Gui

from orville_freecad import metadata


def _addon_root():
    module_file = globals().get("__file__")
    if not module_file:
        module_file = sys._getframe().f_code.co_filename
    return os.path.dirname(os.path.abspath(module_file))


ROOT_DIR = _addon_root()
RESOURCE_DIR = os.path.join(ROOT_DIR, "resources")
ICON_PATH = os.path.join(RESOURCE_DIR, "orville.svg")


class OrvilleWorkbench(Workbench):  # noqa: F821 - provided by FreeCAD at runtime
    MenuText = metadata.WORKBENCH_MENU_TEXT
    ToolTip = metadata.WORKBENCH_TOOLTIP
    Icon = ICON_PATH

    def Initialize(self):
        from orville_freecad.command import COMMANDS, register_commands

        Gui.addIconPath(RESOURCE_DIR)
        register_commands()
        self.appendToolbar(metadata.WORKBENCH_MENU_TEXT, COMMANDS)
        self.appendMenu(metadata.WORKBENCH_MENU_TEXT, COMMANDS)
        App.Console.PrintLog("Orville workbench initialized\n")

    def Activated(self):
        return

    def Deactivated(self):
        return

    def ContextMenu(self, recipient):
        from orville_freecad.command import COMMANDS

        self.appendContextMenu(metadata.WORKBENCH_MENU_TEXT, COMMANDS)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(OrvilleWorkbench())
