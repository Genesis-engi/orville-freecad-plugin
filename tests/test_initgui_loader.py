import builtins
import sys
import types
import unittest


class InitGuiLoaderTests(unittest.TestCase):
    def test_initgui_loads_with_freecad_separate_globals_and_locals(self):
        class Workbench:
            def appendToolbar(self, *args):
                self.toolbar = args

            def appendMenu(self, *args):
                self.menu = args

            def appendContextMenu(self, *args):
                self.context_menu = args

        class Console:
            @staticmethod
            def PrintLog(value):
                pass

        class GuiModule(types.SimpleNamespace):
            def addWorkbench(self, workbench):
                self.workbench = workbench

            def addIconPath(self, path):
                self.icon_path = path

            def addCommand(self, name, command):
                self.command = (name, command)

        fake_gui = GuiModule()
        original_modules = {
            name: sys.modules.get(name)
            for name in ("FreeCAD", "FreeCADGui", "orville_freecad.command")
        }
        sys.modules["FreeCAD"] = types.SimpleNamespace(Console=Console)
        sys.modules["FreeCADGui"] = fake_gui
        sys.modules.pop("orville_freecad.command", None)

        try:
            with open("InitGui.py", encoding="utf-8") as handle:
                code = compile(
                    handle.read(),
                    "C:/Users/ethen/AppData/Roaming/FreeCAD/v1-1/Mod/"
                    "orville-freecad-plugin/./InitGui.py",
                    "exec",
                )

            globals_dict = {
                "__builtins__": builtins.__dict__,
                "Workbench": Workbench,
            }
            locals_dict = {}
            exec(code, globals_dict, locals_dict)
            workbench = fake_gui.workbench

            self.assertEqual(workbench.MenuText, "Orville")
            self.assertEqual(workbench.ToolTip, "Generate CAD with Orville")
            self.assertTrue(
                workbench.Icon.endswith("resources/orville.png")
                or workbench.Icon.endswith("resources\\orville.png")
            )

            workbench.Initialize()

            self.assertEqual(fake_gui.command[0], "Orville_OpenPanel")
            self.assertEqual(workbench.toolbar[0], "Orville")
            self.assertEqual(workbench.menu[0], "Orville")
        finally:
            for name, module in original_modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module


if __name__ == "__main__":
    unittest.main()
