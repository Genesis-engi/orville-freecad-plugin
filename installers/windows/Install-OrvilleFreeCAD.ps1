# Orville FreeCAD Windows installer.
# Installs the addon into the current user's FreeCAD Mod directory.

[CmdletBinding()]
param(
    [string]$ModDir,
    [switch]$NoDependencyInstall,
    [switch]$NoLaunch,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$AddonName = "orville-freecad-plugin"
$RepoZipUrl = "https://github.com/Genesis-engi/orville-freecad-plugin/archive/refs/heads/main.zip"
$DefaultModDir = Join-Path $env:APPDATA "FreeCAD\v1-1\Mod"

if (-not $ModDir) {
    $ModDir = $DefaultModDir
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-FreeCADFile {
    param([string]$FileName)

    $patterns = @()
    if ($env:ProgramFiles) {
        $patterns += Join-Path $env:ProgramFiles "FreeCAD*\bin\$FileName"
        $patterns += Join-Path $env:ProgramFiles "FreeCAD*\$FileName"
    }
    if (${env:ProgramFiles(x86)}) {
        $patterns += Join-Path ${env:ProgramFiles(x86)} "FreeCAD*\bin\$FileName"
        $patterns += Join-Path ${env:ProgramFiles(x86)} "FreeCAD*\$FileName"
    }
    if ($env:LOCALAPPDATA) {
        $patterns += Join-Path $env:LOCALAPPDATA "Programs\FreeCAD*\bin\$FileName"
        $patterns += Join-Path $env:LOCALAPPDATA "Programs\FreeCAD*\$FileName"
    }

    foreach ($pattern in $patterns) {
        $match = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($match) {
            return $match.FullName
        }
    }

    $command = Get-Command $FileName -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    return $null
}

function Install-Keyring {
    if ($NoDependencyInstall) {
        Write-Host "Skipping Python dependency install."
        return
    }

    $python = Find-FreeCADFile "python.exe"
    if (-not $python) {
        Write-Warning "Could not find FreeCAD's python.exe. Orville can still use a session-only API key fallback if keyring is unavailable."
        return
    }

    Write-Step "Checking keyring dependency"
    & $python -c "import keyring" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "keyring is already available in FreeCAD's Python."
        return
    }

    Write-Host "Installing keyring with FreeCAD's Python: $python"
    & $python -m pip install keyring
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not install keyring automatically. Orville can still use a session-only API key fallback."
    }
}

function Install-Addon {
    $target = Join-Path $ModDir $AddonName
    $tempRoot = Join-Path $env:TEMP ("OrvilleFreeCADInstall_" + [guid]::NewGuid().ToString("N"))
    $zipPath = Join-Path $tempRoot "orville-freecad-plugin.zip"
    $extractPath = Join-Path $tempRoot "extract"

    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $extractPath -Force | Out-Null
    New-Item -ItemType Directory -Path $ModDir -Force | Out-Null

    try {
        Write-Step "Downloading Orville"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $RepoZipUrl -OutFile $zipPath -UseBasicParsing

        Write-Step "Extracting package"
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
        $source = Get-ChildItem -Path $extractPath -Directory |
            Where-Object { Test-Path (Join-Path $_.FullName "package.xml") } |
            Select-Object -First 1

        if (-not $source) {
            throw "Downloaded package did not contain package.xml."
        }

        if (Test-Path $target) {
            $existing = Get-Item -LiteralPath $target -Force
            if (($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                Write-Step "Removing existing addon link"
                Remove-Item -LiteralPath $target -Force
            }
            else {
                $backup = "$target.backup-$(Get-Date -Format yyyyMMddHHmmss)"
                Write-Step "Backing up existing addon"
                Move-Item -LiteralPath $target -Destination $backup
                Write-Host "Backup: $backup"
            }
        }

        Write-Step "Installing addon"
        Copy-Item -Path $source.FullName -Destination $target -Recurse -Force
        Write-Host "Installed to: $target"
    }
    finally {
        if (Test-Path $tempRoot) {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function Launch-FreeCAD {
    if ($NoLaunch) {
        return
    }

    $freecad = Find-FreeCADFile "FreeCAD.exe"
    if ($freecad) {
        Write-Step "Launching FreeCAD"
        Start-Process -FilePath $freecad
    }
    else {
        Write-Host "FreeCAD executable was not found automatically. Start FreeCAD manually."
    }
}

Write-Host "Orville FreeCAD Installer" -ForegroundColor Green
Write-Host "Target Mod directory: $ModDir"

if ($DryRun) {
    Write-Host "Dry run only. No files were changed."
    Write-Host "FreeCAD.exe: $(Find-FreeCADFile "FreeCAD.exe")"
    Write-Host "python.exe: $(Find-FreeCADFile "python.exe")"
    exit 0
}

if (Get-Process -Name "FreeCAD" -ErrorAction SilentlyContinue) {
    Write-Warning "FreeCAD appears to be running. Close and restart FreeCAD after this installer finishes."
}

Install-Addon
Install-Keyring
Launch-FreeCAD

Write-Host ""
Write-Host "Done. In FreeCAD, switch to the Orville workbench and click Open Orville." -ForegroundColor Green
Write-Host "API key setup happens on first launch inside Orville."
