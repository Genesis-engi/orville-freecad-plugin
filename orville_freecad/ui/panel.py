"""Dockable Orville chat panel for FreeCAD."""

from __future__ import annotations

import os
import threading
import time
from typing import Optional

from PySide import QtCore, QtGui, QtWidgets

from ..api import OrvilleApiClient, OrvilleApiError
from ..attachments import InvalidImageAttachmentError, build_image_attachments
from ..credentials import CredentialStore, CredentialStoreError, ENV_VAR
from ..import_step import StepImportError, import_step_file, import_step_file_to_new_document
from ..jobs import is_job_active, job_status, step_artifacts, top_level_step_artifact
from ..metadata import PANEL_OBJECT_NAME, PANEL_TITLE
from ..paths import artifact_cache_dir


POLL_INTERVAL_SECONDS = 60
MODE_REVIEW = "Review"
MODE_ITERATE = "Iterate"
REVIEW_PROMPT_PREFIX = (
    "Review the current CAD result for manufacturability, dimensional risks, "
    "fit issues, and concrete improvements. Do not redesign unless explicitly "
    "asked. User request: "
)
ACTION_DOWNLOAD = "download"
ACTION_IMPORT_ACTIVE = "import_active"
ACTION_OPEN_NEW = "open_new"

_panel = None


class _PanelSignals(QtCore.QObject):
    busy_changed = QtCore.Signal(bool)
    log_message = QtCore.Signal(str)
    error_message = QtCore.Signal(str)
    job_updated = QtCore.Signal(object)
    job_completed = QtCore.Signal(object)
    artifact_downloaded = QtCore.Signal(object, object)


class OrvillePanel(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__(PANEL_TITLE, parent)
        self.setObjectName(PANEL_OBJECT_NAME)
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        self.credential_store = CredentialStore()
        self.attachment_paths = []
        self.current_job_id: Optional[str] = None
        self.current_status = ""
        self.downloaded_artifacts = {}
        self.session_api_key: Optional[str] = None
        self.busy_count = 0
        self.signals = _PanelSignals()

        self._build_ui()
        self._connect_signals()
        self._refresh_key_status()

    def _build_ui(self):
        root = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QtWidgets.QHBoxLayout()
        logo_label = QtWidgets.QLabel(root)
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "orville.png")
        pixmap = QtGui.QPixmap(logo_path)
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaled(32, 32, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        header.addWidget(logo_label)

        title = QtWidgets.QLabel("Orville", root)
        title_font = title.font()
        title_font.setPointSize(max(title_font.pointSize() + 3, 13))
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch(1)

        self.status_label = QtWidgets.QLabel(root)
        header.addWidget(self.status_label)
        layout.addLayout(header)

        key_layout = QtWidgets.QHBoxLayout()
        self.api_key_edit = QtWidgets.QLineEdit(root)
        self.api_key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Orville API key")
        key_layout.addWidget(self.api_key_edit, 1)
        self.save_key_button = QtWidgets.QPushButton("Save", root)
        self.clear_key_button = QtWidgets.QPushButton("Clear", root)
        key_layout.addWidget(self.save_key_button)
        key_layout.addWidget(self.clear_key_button)
        layout.addLayout(key_layout)

        self.transcript = QtWidgets.QTextEdit(root)
        self.transcript.setReadOnly(True)
        self.transcript.setMinimumHeight(180)
        layout.addWidget(self.transcript, 1)

        attachment_bar = QtWidgets.QHBoxLayout()
        self.attach_button = QtWidgets.QPushButton("Attach Images", root)
        self.remove_attachment_button = QtWidgets.QPushButton("Remove", root)
        attachment_bar.addWidget(self.attach_button)
        attachment_bar.addWidget(self.remove_attachment_button)
        attachment_bar.addStretch(1)
        layout.addLayout(attachment_bar)

        self.attachments_list = QtWidgets.QListWidget(root)
        self.attachments_list.setMaximumHeight(76)
        layout.addWidget(self.attachments_list)

        self.prompt_edit = QtWidgets.QPlainTextEdit(root)
        self.prompt_edit.setPlaceholderText("Describe the part or the change you want.")
        self.prompt_edit.setFixedHeight(92)
        layout.addWidget(self.prompt_edit)

        mode_bar = QtWidgets.QHBoxLayout()
        mode_label = QtWidgets.QLabel("Mode", root)
        self.review_mode_button = QtWidgets.QPushButton(MODE_REVIEW, root)
        self.iterate_mode_button = QtWidgets.QPushButton(MODE_ITERATE, root)
        self.mode_button_group = QtWidgets.QButtonGroup(root)
        self.mode_button_group.setExclusive(True)

        for button in (self.review_mode_button, self.iterate_mode_button):
            button.setCheckable(True)
            button.setMinimumHeight(26)
            button.setStyleSheet(
                """
                QPushButton {
                    padding: 3px 14px;
                    border: 1px solid #4b5563;
                    background: #24292f;
                    color: #d0d7de;
                }
                QPushButton:checked {
                    background: #f59e0b;
                    border-color: #f59e0b;
                    color: #111827;
                    font-weight: 600;
                }
                """
            )

        self.review_mode_button.setChecked(True)
        self.review_mode_button.setToolTip("Ask Orville to critique the current result.")
        self.iterate_mode_button.setToolTip("Ask Orville to revise the current result.")
        self.mode_button_group.addButton(self.review_mode_button)
        self.mode_button_group.addButton(self.iterate_mode_button)
        mode_bar.addWidget(mode_label)
        mode_bar.addWidget(self.review_mode_button)
        mode_bar.addWidget(self.iterate_mode_button)
        mode_bar.addStretch(1)
        layout.addLayout(mode_bar)

        self.auto_open_checkbox = QtWidgets.QCheckBox("Open result in new tab", root)
        self.auto_open_checkbox.setChecked(True)
        self.auto_open_checkbox.setToolTip("Automatically open the top-level STEP result in a new FreeCAD document.")
        layout.addWidget(self.auto_open_checkbox)

        send_bar = QtWidgets.QHBoxLayout()
        send_bar.addStretch(1)
        self.send_button = QtWidgets.QPushButton("Send", root)
        send_bar.addWidget(self.send_button)
        layout.addLayout(send_bar)

        artifact_label = QtWidgets.QLabel("STEP Artifacts", root)
        layout.addWidget(artifact_label)

        self.artifact_list = QtWidgets.QListWidget(root)
        self.artifact_list.setMaximumHeight(96)
        layout.addWidget(self.artifact_list)

        artifact_buttons = QtWidgets.QHBoxLayout()
        self.download_button = QtWidgets.QPushButton("Download", root)
        self.import_button = QtWidgets.QPushButton("Import", root)
        artifact_buttons.addWidget(self.download_button)
        artifact_buttons.addWidget(self.import_button)
        artifact_buttons.addStretch(1)
        layout.addLayout(artifact_buttons)

        self.setWidget(root)

    def _connect_signals(self):
        self.save_key_button.clicked.connect(self._save_api_key)
        self.clear_key_button.clicked.connect(self._clear_api_key)
        self.attach_button.clicked.connect(self._attach_images)
        self.remove_attachment_button.clicked.connect(self._remove_selected_attachment)
        self.send_button.clicked.connect(self._send_prompt)
        self.download_button.clicked.connect(lambda: self._download_selected_artifact(ACTION_DOWNLOAD))
        self.import_button.clicked.connect(lambda: self._download_selected_artifact(ACTION_IMPORT_ACTIVE))

        self.signals.busy_changed.connect(self._set_busy)
        self.signals.log_message.connect(self._append_log)
        self.signals.error_message.connect(self._show_error)
        self.signals.job_updated.connect(self._job_updated)
        self.signals.job_completed.connect(self._job_completed)
        self.signals.artifact_downloaded.connect(self._artifact_downloaded)

    def _refresh_key_status(self):
        try:
            stored_key = self.credential_store.get_api_key()
        except CredentialStoreError as exc:
            self.status_label.setText("Key store unavailable")
            self._append_system(str(exc))
            return

        if os.getenv(ENV_VAR):
            self.status_label.setText(f"Using {ENV_VAR}")
        elif stored_key:
            self.status_label.setText("API key saved")
        elif self.session_api_key:
            self.status_label.setText("API key in session")
        else:
            self.status_label.setText("API key needed")

    def _save_api_key(self):
        api_key = self.api_key_edit.text().strip()
        try:
            self.credential_store.set_api_key(api_key)
        except (CredentialStoreError, ValueError) as exc:
            if not api_key:
                self._show_error(str(exc))
                return
            self.session_api_key = api_key
            self.api_key_edit.clear()
            self._refresh_key_status()
            self._append_system(
                "API key kept in memory for this FreeCAD session because secure OS storage is unavailable."
            )
            return

        self.api_key_edit.clear()
        self._refresh_key_status()
        self._append_system("API key saved to secure OS storage.")

    def _clear_api_key(self):
        self.session_api_key = None
        try:
            self.credential_store.delete_api_key()
        except CredentialStoreError as exc:
            self._append_system(str(exc))

        self._refresh_key_status()
        self._append_system("API key cleared.")

    def _get_api_key(self) -> Optional[str]:
        try:
            return self.credential_store.get_api_key() or self.session_api_key
        except CredentialStoreError:
            return self.session_api_key

    def _attach_images(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Attach Images",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.gif *.heic *.heif)",
        )
        if not files:
            return

        combined = list(dict.fromkeys(self.attachment_paths + list(files)))
        try:
            build_image_attachments(combined)
        except InvalidImageAttachmentError as exc:
            self._show_error(str(exc))
            return

        self.attachment_paths = combined
        self._render_attachments()

    def _remove_selected_attachment(self):
        selected = self.attachments_list.currentRow()
        if selected < 0:
            return
        del self.attachment_paths[selected]
        self._render_attachments()

    def _render_attachments(self):
        self.attachments_list.clear()
        for path in self.attachment_paths:
            self.attachments_list.addItem(os.path.basename(path))

    def _send_prompt(self):
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            self._show_error("Prompt is required.")
            return

        api_key = self._get_api_key()

        if not api_key:
            self._show_error(f"Paste an API key and click Save, or set {ENV_VAR}.")
            return

        if self.current_job_id and self.current_status in {"queued", "running"}:
            self._show_error("Current job is still running.")
            return

        images = list(self.attachment_paths)
        followup_job_id = self.current_job_id
        mode = self._selected_mode()
        api_prompt = self._prompt_for_mode(prompt, bool(followup_job_id), mode)
        self._append_user(prompt)
        self.prompt_edit.clear()
        self.attachment_paths = []
        self._render_attachments()
        self.artifact_list.clear()
        self.signals.busy_changed.emit(True)

        thread = threading.Thread(
            target=self._submit_and_poll,
            args=(api_key, api_prompt, images, followup_job_id, mode),
            daemon=True,
        )
        thread.start()

    def _prompt_for_mode(self, prompt: str, has_existing_job: bool, mode: str) -> str:
        if has_existing_job and mode == MODE_REVIEW:
            return f"{REVIEW_PROMPT_PREFIX}{prompt}"
        return prompt

    def _selected_mode(self) -> str:
        if self.iterate_mode_button.isChecked():
            return MODE_ITERATE
        return MODE_REVIEW

    def _submit_and_poll(
        self,
        api_key: str,
        prompt: str,
        images: list[str],
        followup_job_id: Optional[str],
        mode: str,
    ):
        client = OrvilleApiClient(api_key)
        try:
            if followup_job_id:
                job = client.create_message(followup_job_id, prompt, images)
                job_id = job.get("id") or followup_job_id
                self.signals.log_message.emit(f"{mode} queued.")
            else:
                job = client.create_job(prompt, images)
                job_id = job.get("id")
                self.signals.log_message.emit("Design queued.")

            if not job_id:
                raise OrvilleApiError(None, "missing_job_id", "Orville did not return a job id.")

            self.signals.job_updated.emit(job)
            while is_job_active(job):
                time.sleep(POLL_INTERVAL_SECONDS)
                job = client.get_job(job_id)
                self.signals.job_updated.emit(job)

            self.signals.job_completed.emit(job)
        except Exception as exc:
            self.signals.error_message.emit(_clean_error_message(exc))
        finally:
            self.signals.busy_changed.emit(False)

    def _job_updated(self, job: dict):
        self.current_job_id = job.get("id") or self.current_job_id
        self.current_status = job_status(job)
        self.status_label.setText(self.current_status.title() or "Working")

    def _job_completed(self, job: dict):
        self._job_updated(job)
        status = job_status(job)
        explanation = job.get("explanation")
        if explanation:
            self._append_orville(explanation)

        if status == "failed":
            self._show_error("Orville job failed.")
            return

        artifacts = step_artifacts(job)
        self.artifact_list.clear()
        for artifact in artifacts:
            item = QtWidgets.QListWidgetItem(artifact.get("filename") or artifact.get("id") or "STEP artifact")
            item.setData(QtCore.Qt.UserRole, artifact)
            self.artifact_list.addItem(item)

        if artifacts:
            self._append_system(f"{len(artifacts)} STEP artifact(s) ready.")
            if self.auto_open_checkbox.isChecked():
                self._auto_open_job_result(job)
        else:
            self._append_system("Job completed with no STEP artifact.")

    def _auto_open_job_result(self, job: dict):
        artifact = top_level_step_artifact(job)
        if not artifact:
            return
        self._append_system("Opening top-level result in a new tab.")
        self._download_artifact(artifact, ACTION_OPEN_NEW)

    def _download_selected_artifact(self, action: str):
        item = self.artifact_list.currentItem()
        if item is None:
            self._show_error("Select a STEP artifact.")
            return

        artifact = item.data(QtCore.Qt.UserRole)
        self._download_artifact(artifact, action)

    def _download_artifact(self, artifact: dict, action: str):
        artifact_id = artifact.get("id") or artifact.get("artifact_id")
        if not artifact_id:
            self._show_error("Selected artifact has no id.")
            return

        existing_path = self.downloaded_artifacts.get(artifact_id)
        if existing_path and os.path.exists(existing_path):
            if action == ACTION_IMPORT_ACTIVE:
                self._import_downloaded_step(existing_path)
            elif action == ACTION_OPEN_NEW:
                self._open_downloaded_step(existing_path, artifact.get("filename"))
            else:
                self._append_system("STEP artifact already downloaded.")
            return

        api_key = self._get_api_key()

        if not api_key:
            self._show_error(f"Paste an API key and click Save, or set {ENV_VAR}.")
            return

        self.signals.busy_changed.emit(True)
        thread = threading.Thread(
            target=self._download_artifact_worker,
            args=(api_key, artifact, action),
            daemon=True,
        )
        thread.start()

    def _download_artifact_worker(self, api_key: str, artifact: dict, action: str):
        client = OrvilleApiClient(api_key)
        try:
            artifact_id = artifact.get("id") or artifact.get("artifact_id")
            download = client.download_artifact(
                artifact_id,
                artifact_cache_dir(),
                filename=artifact.get("filename"),
            )
            self.signals.artifact_downloaded.emit(download, action)
        except Exception as exc:
            self.signals.error_message.emit(_clean_error_message(exc))
        finally:
            self.signals.busy_changed.emit(False)

    def _artifact_downloaded(self, download, action: str):
        self.downloaded_artifacts[download.artifact_id] = download.path
        self._append_system("Downloaded STEP artifact.")
        if action == ACTION_IMPORT_ACTIVE:
            self._import_downloaded_step(download.path)
        elif action == ACTION_OPEN_NEW:
            self._open_downloaded_step(download.path, download.filename)

    def _import_downloaded_step(self, path: str):
        try:
            import_step_file(path)
        except StepImportError as exc:
            self._show_error(str(exc))
            return
        self._append_system("Imported STEP artifact into the active document.")

    def _open_downloaded_step(self, path: str, document_name: Optional[str] = None):
        try:
            opened_name = import_step_file_to_new_document(path, document_name)
        except StepImportError as exc:
            self._show_error(str(exc))
            return
        self._append_system(f"Opened result in new tab: {opened_name}.")

    def _set_busy(self, busy: bool):
        if busy:
            self.busy_count += 1
        else:
            self.busy_count = max(0, self.busy_count - 1)

        is_busy = self.busy_count > 0
        self.send_button.setEnabled(not is_busy)
        self.download_button.setEnabled(not is_busy)
        self.import_button.setEnabled(not is_busy)
        if is_busy:
            self.status_label.setText("Working")
        elif self.current_status:
            self.status_label.setText(self.current_status.title())
        else:
            self._refresh_key_status()

    def _append_log(self, message: str):
        self._append_system(message)

    def _append_system(self, message: str):
        self._append_message("System", message, "#8a949e", "#8a949e", "12px")

    def _append_user(self, message: str):
        self._append_message("You", message, "#d0d7de", "#58a6ff", "13px")

    def _append_orville(self, message: str):
        self._append_message("Orville", message, "#f2f4f8", "#f59e0b", "13px")

    def _append_message(self, label: str, message: str, body_color: str, label_color: str, size: str):
        html = (
            f'<div style="margin: 0 0 8px 0; color: {body_color}; font-size: {size};">'
            f'<span style="font-weight: 700; color: {label_color};">{_escape_html(label)}</span>'
            f'<span style="color: {body_color};"> {_escape_html(message)}</span>'
            "</div>"
        )
        self.transcript.append(html)

    def _show_error(self, message: str):
        self._append_message("Error", message, "#ffb4ab", "#ff6b6b", "13px")
        QtWidgets.QMessageBox.warning(self, "Orville", message)


def show_panel():
    global _panel

    import FreeCADGui as Gui

    main_window = Gui.getMainWindow()
    if _panel is None:
        _panel = OrvillePanel(main_window)
        main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, _panel)

    _panel.show()
    _panel.raise_()
    return _panel


def _clean_error_message(exc: Exception) -> str:
    if isinstance(exc, OrvilleApiError):
        if exc.status_code:
            return f"{exc.message} ({exc.code}, HTTP {exc.status_code})"
        return f"{exc.message} ({exc.code})"
    return str(exc)


def _escape_html(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
