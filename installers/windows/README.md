# Windows Installer

The public Windows download should be the Inno Setup wizard built from:

```text
installers/windows/OrvilleFreeCAD.iss
```

The installer is a per-user setup wizard. It installs Orville into the user's FreeCAD 1.1 addon directory:

```text
%APPDATA%\FreeCAD\v1-1\Mod\orville-freecad-plugin
```

## User Experience

- Standard Windows setup wizard.
- No administrator rights required.
- Optional `keyring` dependency install through FreeCAD's Python.
- Optional FreeCAD launch after setup.
- API key entry stays inside Orville on first launch.

## Build Locally

Install Inno Setup 6, then run:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installers\windows\OrvilleFreeCAD.iss"
```

The output is:

```text
dist\windows\Orville-FreeCAD-Setup.exe
```

## Build In GitHub Actions

Run the `Build Windows Installer` workflow manually, or push a `v*` tag. The workflow uploads `Orville-FreeCAD-Setup.exe` as an artifact.

## Internal Fallback

`Install-OrvilleFreeCAD.ps1` and `Install-OrvilleFreeCAD.cmd` remain as script-based internal fallback installers. They are not the preferred website download.
