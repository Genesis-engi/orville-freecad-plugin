# Orville FreeCAD Plugin Plan

Date: 2026-05-22
Target CAD package: FreeCAD
Repo status: First implementation slice in progress

## Source Material

- Product spec: `../CAD_plugin_spec.md`
- Orville CAD API base URL: `https://www.ballistalabs.ai`
- Orville API machine reference: `https://www.ballistalabs.ai/api/v1/openapi.json`
- FreeCAD latest release check: `https://github.com/FreeCAD/FreeCAD` reports FreeCAD 1.1.1 as the latest release on 2026-04-14.
- FreeCAD developer dependencies: `https://freecad.github.io/DevelopersHandbook/gettingstarted/dependencies.html`
- FreeCAD workbench creation docs: `https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/Workbench_creation.md`
- FreeCAD package metadata docs: `https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/Package_Metadata.md`
- FreeCAD Addon Manager docs: `https://github.com/FreeCAD/AddonManager`
- FreeCAD standard import docs: `https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/Std_Import.md`

## FreeCAD Constraints To Respect

- Build this as an external Python-only FreeCAD workbench.
- Use the standard FreeCAD addon layout: top-level `Init.py`, `InitGui.py`, `package.xml`, resources, and Python modules.
- Keep GUI code under `InitGui.py`/Workbench command loading so FreeCAD console mode is not forced to load UI code.
- Import Qt via `from PySide import ...` instead of `PySide2` or `PySide6`, matching current FreeCAD guidance for Qt compatibility.
- Target FreeCAD 1.1.x stable first while avoiding choices that block FreeCAD 1.2 development builds.
- Use `package.xml` format 1 metadata with required name, version, date, description, maintainer, SPDX license, icon, content, and workbench classname.
- Prefer standard FreeCAD import behavior for STEP files. The plugin should not parse STEP itself.

## Product Requirements

- Show an Orville chat panel inside FreeCAD.
- Let users attach up to five reference images with validation before upload.
- Let users send an initial prompt and follow-up prompts for iteration.
- Store the Orville API key securely.
- Create CAD jobs, poll status, show running/completed/failed state, and surface errors clearly.
- Download completed STEP artifacts.
- Let the user import a downloaded STEP artifact into the current FreeCAD document/workspace through FreeCAD's normal import path.
- Include Orville branding if assets are available and license-cleared.

## Architecture

- `Init.py`: minimal app-side initialization only.
- `InitGui.py`: registers `OrvilleWorkbench` and the command that opens the UI.
- `orville_freecad/ui/`: PySide dock widget or task panel for chat, attachments, status, and artifact actions.
- `orville_freecad/api.py`: Orville API client using standard-library HTTP where practical, with idempotency key generation and multipart upload support.
- `orville_freecad/credentials.py`: key storage abstraction. Use OS-backed `keyring` when available; do not persist API keys in plaintext. Allow `ORVILLE_API_KEY` only as a non-persisted development override.
- `orville_freecad/jobs.py`: local job state, polling cadence, artifact metadata, and download paths.
- `orville_freecad/import_step.py`: FreeCAD import adapter using the standard import stack, likely `ImportGui.insert(path, active_document_name)` after confirming behavior in FreeCAD 1.1.x. If FreeCAD exposes a better way to invoke the built-in import command with a preselected file, prefer that.
- `resources/`: icon/logo assets, qrc file, generated resource module if needed.
- `tests/`: unit tests for API request building, credential behavior, job state transitions, and import adapter boundaries with FreeCAD mocked.

## API Plan

- Authentication: `Authorization: Bearer <api_key>`.
- Create job:
  - `POST /api/v1/cad/jobs`
  - JSON when no images are attached.
  - Multipart form data with field name `images` when images are attached.
  - Always send a unique `Idempotency-Key` for write requests.
- List recent jobs:
  - `GET /api/v1/cad/jobs`
  - Use `limit` and the opaque `cursor` for pagination.
  - Show jobs from both `webapp` and `api` sources so users can continue workspace work from FreeCAD.
- Load message history:
  - `GET /api/v1/cad/jobs/{job_id}/messages`
  - Render only public user and assistant messages; system/internal messages are not exposed by the API.
- Poll job:
  - `GET /api/v1/cad/jobs/{job_id}`
  - Use `poll_after_seconds` when present, falling back to 60 seconds, until `completed` or `failed`.
- Iterate:
  - `POST /api/v1/cad/jobs/{job_id}/messages`
  - Only allow follow-ups after the current run is not actively running.
- Review:
  - `POST /api/v1/cad/jobs/{job_id}/review`
  - Use the synchronous review assistant endpoint for completed jobs.
  - Do not start polling because review responses do not queue CAD iterations.
- Download STEP:
  - Use artifact `download_url` from completed job response.
  - Follow redirects or request `redirect=false` if direct download handling is easier in FreeCAD's Python runtime.

## UI Plan

- Workbench command opens a persistent dockable chat panel.
- Top area: API key status and connect/settings action.
- Middle area: message transcript with job status rows, generated explanations, and a collapsible searchable recent job list.
- Composer: prompt input, attach image button, attached image list with remove actions, send button.
- Completion state: artifact list with `Download`, `Import into current document`, automatic top-level result open, and `New Chat` for starting the next job.
- Notifications: update FreeCAD report/status output and show a Qt dialog or non-blocking banner when a job completes or fails.
- Respect FreeCAD UI conventions: toolbars/menus for commands, dialog/task panel for settings, and no custom CAD viewport rendering unless needed.

## Security Plan

- Never write the API key to repo files, FreeCAD project files, logs, or plaintext preferences.
- Use the Python `keyring` package for OS credential storage where available.
- If `keyring` is unavailable or no backend exists, prompt the user to install/configure a supported backend instead of silently falling back to plaintext.
- Redact API keys from exceptions, report view messages, and debug logs.
- Store downloaded STEP artifacts under a user-chosen or plugin-managed cache directory with predictable cleanup.

## Import Plan

- Validate active document before import; create a document only if the user explicitly chooses that behavior.
- Use FreeCAD's standard import machinery for STEP, not a custom parser.
- Preserve user import preferences where FreeCAD's import stack applies them.
- After import, recompute the document and fit view if appropriate.
- Keep the downloaded STEP path available so users can also import manually through `File > Import...`.

## Packaging Plan

- Add `package.xml` before first functional release.
- Include an icon referenced by both the workbench class and package metadata.
- Include `requirements.txt` only for dependencies that are actually required by the Addon Manager install path.
- Document manual install by copying/cloning into the FreeCAD user `Mod` directory.
- Add release tags using semantic versioning.

## Development Milestones

1. Done: Bootstrap repo metadata: README, license, gitignore, this plan.
2. Done: Add FreeCAD workbench skeleton with `Init.py`, `InitGui.py`, command registration, icon, and `package.xml`.
3. Done: Build secure credential flow and API key settings UI.
4. Done: Implement Orville API client with mocked tests for create, iterate, artifacts, download, and error handling.
5. Done: Build chat panel with prompt submission, image picker, validation, and job state display.
6. Done: Add background polling with UI-thread signal updates.
7. Done: Add STEP artifact download and import into the active document through FreeCAD's import stack.
8. Done: Add recent job loading, public chat-history restore, new chat reset, and default iterate mode for new chats.
9. Done: Switch review mode from prompt-prefix follow-up to the dedicated review assistant endpoint.
10. Next: Add end-to-end manual validation notes for FreeCAD 1.1.x on Windows, macOS, and Linux.
11. Next: Prepare Addon Manager readiness docs and contribution guidelines.

## Open Questions

- Confirm final Orville logo asset, dimensions, and license.
- Decide whether MIT remains the intended license or whether LGPL-2.1-or-later is preferred for closer FreeCAD ecosystem alignment.
- Confirm maintainer name/email for `package.xml`.
- Confirm whether downloaded STEP files should live in a plugin cache, beside the current `.FCStd` document, or in a user-selected folder.
- Validate in FreeCAD whether invoking `ImportGui.insert` is sufficient to match the post-file-picker behavior for STEP import in the latest stable release.
