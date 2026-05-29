# Install Workflow E2E Test

## Current Install State

- The addon has standard package metadata in `package.xml`.
- `keyring` is declared as a Python dependency.
- `scripts/install_freecad_addon.py` supports agent-assisted install/update.
- `installers/windows/OrvilleFreeCAD.iss` builds the standard Windows setup wizard.
- First launch prompts for an API key if none is configured.
- API key can be changed later from Settings.
- If secure credential storage is unavailable, the key can be kept for the current session only.

## What Is Left

- Build and test `Orville-FreeCAD-Setup.exe` on Windows.
- Test Addon Manager install from a clean user profile.
- Test agent-assisted install with `FreeCADCmd scripts/install_freecad_addon.py --install-deps`.
- Confirm Addon Manager installs or prompts for the `keyring` dependency.
- Confirm API key storage persists after app restart when `keyring` is available.
- Confirm session-only API key fallback behaves clearly when `keyring` is unavailable.
- Confirm clean upgrade behavior from an older installed copy.
- Submit or configure the final central Addon Manager source after custom repository testing passes.

## End-To-End Test Pass

1. Install the addon into a clean environment.
2. Launch the CAD package.
3. Confirm the Orville entry appears.
4. Open Orville.
5. Confirm first launch blocks on API key setup.
6. Enter and save an API key.
7. Restart the CAD package.
8. Confirm the API key is still configured.
9. Submit a new CAD job.
10. Confirm job status updates until completion.
11. Confirm the top-level result opens automatically.
12. Start a new chat.
13. Search recent jobs and restore one.
14. Run Review against a completed job.
15. Run Iterate against a completed job.

## Failure Notes To Capture

- Install source used.
- App version and OS.
- Whether `keyring` was installed.
- Whether API key persisted after restart.
- Any report/log errors during startup.
- Whether generated artifacts downloaded and opened.
