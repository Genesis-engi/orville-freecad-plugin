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
from ..import_step import StepImportError, import_step_file
from ..jobs import is_job_active, job_status, step_artifacts
from ..metadata import PANEL_OBJECT_NAME, PANEL_TITLE
from ..paths import artifact_cache_dir


POLL_INTERVAL_SECONDS = 60

_panel = None


class _PanelSignals(QtCore.QObject):
    busy_changed = QtCore.Signal(bool)
    log_message = QtCore.Signal(str)
    error_message = QtCore.Signal(str)
    job_updated = QtCore.Signal(object)
    job_completed = QtCore.Signal(object)
    artifact_downloaded = QtCore.Signal(object, bool)


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
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "orville.svg")
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
        self.download_button.clicked.connect(lambda: self._download_selected_artifact(import_after=False))
        self.import_button.clicked.connect(lambda: self._download_selected_artifact(import_after=True))

        self.signals.busy_changed.connect(self._set_busy)
        self.signals.log_message.connect(self._append_log)
        self.signals.error_message.connect(self._show_error)
        self.signals.job_updated.connect(self._job_updated)
        self.signals.job_completed.connect(self._job_completed)
        self.signals.artifact_downloaded.connect(self._artifact_downloaded)

    def _refresh_key_status(self):
        try:
            key = self.credential_store.get_api_key()
        except CredentialStoreError as exc:
            self.status_label.setText("Key store unavailable")
            self._append_log(str(exc))
            return

        if os.getenv(ENV_VAR):
            self.status_label.setText(f"Using {ENV_VAR}")
        elif key:
            self.status_label.setText("API key saved")
        else:
            self.status_label.setText("API key needed")

    def _save_api_key(self):
        api_key = self.api_key_edit.text().strip()
        try:
            self.credential_store.set_api_key(api_key)
        except (CredentialStoreError, ValueError) as exc:
            self._show_error(str(exc))
            return

        self.api_key_edit.clear()
        self._refresh_key_status()
        self._append_log("API key saved to the OS credential store.")

    def _clear_api_key(self):
        try:
            self.credential_store.delete_api_key()
        except CredentialStoreError as exc:
            self._show_error(str(exc))
            return

        self._refresh_key_status()
        self._append_log("API key removed from the OS credential store.")

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

        try:
            api_key = self.credential_store.get_api_key()
        except CredentialStoreError as exc:
            self._show_error(str(exc))
            return

        if not api_key:
            self._show_error(f"Save an API key or set {ENV_VAR}.")
            return

        if self.current_job_id and self.current_status in {"queued", "running"}:
            self._show_error("Current job is still running.")
            return

        images = list(self.attachment_paths)
        followup_job_id = self.current_job_id
        self._append_log(f"You: {prompt}")
        self.prompt_edit.clear()
        self.attachment_paths = []
        self._render_attachments()
        self.artifact_list.clear()
        self.signals.busy_changed.emit(True)

        thread = threading.Thread(
            target=self._submit_and_poll,
            args=(api_key, prompt, images, followup_job_id),
            daemon=True,
        )
        thread.start()

    def _submit_and_poll(self, api_key: str, prompt: str, images: list[str], followup_job_id: Optional[str]):
        client = OrvilleApiClient(api_key)
        try:
            if followup_job_id:
                job = client.create_message(followup_job_id, prompt, images)
                job_id = job.get("id") or followup_job_id
                self.signals.log_message.emit(f"Orville: iteration queued for {job_id}.")
            else:
                job = client.create_job(prompt, images)
                job_id = job.get("id")
                self.signals.log_message.emit(f"Orville: job queued as {job_id}.")

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
            self._append_log(f"Orville: {explanation}")

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
            self._append_log(f"Orville: {len(artifacts)} STEP artifact(s) ready.")
            QtWidgets.QMessageBox.information(self, "Orville", "STEP artifact ready.")
        else:
            self._append_log("Orville: job completed with no STEP artifact.")

    def _download_selected_artifact(self, import_after: bool):
        item = self.artifact_list.currentItem()
        if item is None:
            self._show_error("Select a STEP artifact.")
            return

        artifact = item.data(QtCore.Qt.UserRole)
        artifact_id = artifact.get("id") or artifact.get("artifact_id")
        if not artifact_id:
            self._show_error("Selected artifact has no id.")
            return

        existing_path = self.downloaded_artifacts.get(artifact_id)
        if existing_path and os.path.exists(existing_path):
            if import_after:
                self._import_downloaded_step(existing_path)
            else:
                self._append_log(f"Downloaded: {existing_path}")
            return

        try:
            api_key = self.credential_store.get_api_key()
        except CredentialStoreError as exc:
            self._show_error(str(exc))
            return

        if not api_key:
            self._show_error(f"Save an API key or set {ENV_VAR}.")
            return

        self.signals.busy_changed.emit(True)
        thread = threading.Thread(
            target=self._download_artifact_worker,
            args=(api_key, artifact, import_after),
            daemon=True,
        )
        thread.start()

    def _download_artifact_worker(self, api_key: str, artifact: dict, import_after: bool):
        client = OrvilleApiClient(api_key)
        try:
            artifact_id = artifact.get("id") or artifact.get("artifact_id")
            download = client.download_artifact(
                artifact_id,
                artifact_cache_dir(),
                filename=artifact.get("filename"),
            )
            self.signals.artifact_downloaded.emit(download, import_after)
        except Exception as exc:
            self.signals.error_message.emit(_clean_error_message(exc))
        finally:
            self.signals.busy_changed.emit(False)

    def _artifact_downloaded(self, download, import_after: bool):
        self.downloaded_artifacts[download.artifact_id] = download.path
        self._append_log(f"Downloaded: {download.path}")
        if import_after:
            self._import_downloaded_step(download.path)

    def _import_downloaded_step(self, path: str):
        try:
            import_step_file(path)
        except StepImportError as exc:
            self._show_error(str(exc))
            return
        self._append_log(f"Imported: {path}")

    def _set_busy(self, busy: bool):
        self.send_button.setEnabled(not busy)
        self.download_button.setEnabled(not busy)
        self.import_button.setEnabled(not busy)
        if busy:
            self.status_label.setText("Working")
        elif self.current_status:
            self.status_label.setText(self.current_status.title())
        else:
            self._refresh_key_status()

    def _append_log(self, message: str):
        self.transcript.append(_escape_html(message))

    def _show_error(self, message: str):
        self._append_log(f"Error: {message}")
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
