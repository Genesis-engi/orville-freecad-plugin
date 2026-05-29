#define AppName "Orville FreeCAD Plugin"
#define AppVersion "0.1.0"
#define AppPublisher "Genesis Engineering"
#define SourceRoot "..\.."

[Setup]
AppId={{C0F0A658-6E0B-41CF-B534-9F8C38BE2851}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/Genesis-engi/orville-freecad-plugin
AppSupportURL=https://github.com/Genesis-engi/orville-freecad-plugin/issues
AppUpdatesURL=https://github.com/Genesis-engi/orville-freecad-plugin/releases
DefaultDirName={userappdata}\FreeCAD\v1-1\Mod\orville-freecad-plugin
DefaultGroupName=Orville FreeCAD Plugin
DisableProgramGroupPage=yes
OutputDir={#SourceRoot}\dist\windows
OutputBaseFilename=Orville-FreeCAD-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupLogging=yes
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Installer for the Orville FreeCAD plugin
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "deps\keyring"; Description: "Install or update the Python keyring dependency"; Flags: checkedonce
Name: "launch"; Description: "Launch FreeCAD after installation"; Flags: unchecked

[Files]
Source: "{#SourceRoot}\Init.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\InitGui.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\package.xml"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\orville_freecad\*"; DestDir: "{app}\orville_freecad"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\orville_freecad\__pycache__"
Type: filesandordirs; Name: "{app}\orville_freecad\ui\__pycache__"

[Code]
function AddTrailingBackslash(Value: String): String;
begin
  Result := Value;
  if (Length(Result) > 0) and (Copy(Result, Length(Result), 1) <> '\') then
    Result := Result + '\';
end;

function FindFirstExistingFile(Path1, Path2, Path3, Path4: String): String;
begin
  Result := '';
  if (Path1 <> '') and FileExists(Path1) then
    Result := Path1
  else if (Path2 <> '') and FileExists(Path2) then
    Result := Path2
  else if (Path3 <> '') and FileExists(Path3) then
    Result := Path3
  else if (Path4 <> '') and FileExists(Path4) then
    Result := Path4;
end;

function FindFreeCADRootFile(FileName: String): String;
var
  ProgramFiles: String;
  ProgramFilesX86: String;
  LocalAppData: String;
begin
  ProgramFiles := GetEnv('ProgramFiles');
  ProgramFilesX86 := GetEnv('ProgramFiles(x86)');
  LocalAppData := GetEnv('LOCALAPPDATA');
  Result := FindFirstExistingFile(
    AddTrailingBackslash(ProgramFiles) + 'FreeCAD 1.1\bin\' + FileName,
    AddTrailingBackslash(ProgramFiles) + 'FreeCAD 1.0\bin\' + FileName,
    AddTrailingBackslash(ProgramFilesX86) + 'FreeCAD 1.1\bin\' + FileName,
    AddTrailingBackslash(LocalAppData) + 'Programs\FreeCAD 1.1\bin\' + FileName
  );
end;

function FindFreeCADPython(): String;
var
  CmdLine: String;
  ResultCode: Integer;
  TempFile: String;
  Lines: TArrayOfString;
begin
  Result := FindFreeCADRootFile('python.exe');
  if Result <> '' then
    Exit;

  TempFile := ExpandConstant('{tmp}\orville-freecad-python-path.txt');
  CmdLine := '/C where python.exe > "' + TempFile + '"';
  if Exec(ExpandConstant('{cmd}'), CmdLine, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then begin
    if LoadStringsFromFile(TempFile, Lines) and (GetArrayLength(Lines) > 0) then
      Result := Lines[0];
  end;
end;

function FindFreeCADExe(): String;
var
  CmdLine: String;
  ResultCode: Integer;
  TempFile: String;
  Lines: TArrayOfString;
begin
  Result := FindFreeCADRootFile('FreeCAD.exe');
  if Result <> '' then
    Exit;

  TempFile := ExpandConstant('{tmp}\orville-freecad-exe-path.txt');
  CmdLine := '/C where FreeCAD.exe > "' + TempFile + '"';
  if Exec(ExpandConstant('{cmd}'), CmdLine, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then begin
    if LoadStringsFromFile(TempFile, Lines) and (GetArrayLength(Lines) > 0) then
      Result := Lines[0];
  end;
end;

procedure InstallKeyring();
var
  PythonPath: String;
  ResultCode: Integer;
begin
  PythonPath := FindFreeCADPython();
  if PythonPath = '' then begin
    MsgBox('Orville was installed, but Setup could not find FreeCAD''s python.exe to install keyring. Orville can still use a session-only API key fallback.', mbInformation, MB_OK);
    Exit;
  end;

  Exec(PythonPath, '-c "import keyring"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if ResultCode = 0 then
    Exit;

  if not Exec(PythonPath, '-m pip install keyring', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    MsgBox('Orville was installed, but Setup could not install keyring automatically. Orville can still use a session-only API key fallback.', mbInformation, MB_OK);
end;

procedure LaunchFreeCAD();
var
  FreeCADPath: String;
  ResultCode: Integer;
begin
  FreeCADPath := FindFreeCADExe();
  if FreeCADPath = '' then begin
    MsgBox('Setup could not find FreeCAD.exe automatically. Start FreeCAD manually, then open the Orville workbench.', mbInformation, MB_OK);
    Exit;
  end;

  Exec(FreeCADPath, '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    if WizardIsTaskSelected('deps\keyring') then
      InstallKeyring();
    if WizardIsTaskSelected('launch') then
      LaunchFreeCAD();
  end;
end;
