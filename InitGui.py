"""FreeCAD GUI registration for the Orville workbench."""

import importlib as _importlib
import os as _os
import sys as _sys

_globals = globals()
_globals["_os"] = _os
_globals["_sys"] = _sys
_globals["App"] = _importlib.import_module("FreeCAD")
_globals["Gui"] = _importlib.import_module("FreeCADGui")
_globals["metadata"] = _importlib.import_module("orville_freecad.metadata")


def _addon_root():
    module_file = globals().get("__file__")
    if not module_file:
        module_file = _sys._getframe().f_code.co_filename
    return _os.path.dirname(_os.path.abspath(module_file))


_globals["ROOT_DIR"] = _addon_root()
_globals["RESOURCE_DIR"] = _os.path.join(_globals["ROOT_DIR"], "resources")
_globals["ICON_PATH"] = _os.path.join(_globals["RESOURCE_DIR"], "orville.png")


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
