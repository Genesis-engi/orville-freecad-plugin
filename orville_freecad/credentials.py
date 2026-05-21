"""Secure API key storage for the Orville FreeCAD workbench."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import sys
from typing import Optional


ENV_VAR = "ORVILLE_API_KEY"
SERVICE_NAME = "Orville FreeCAD Workbench"
ACCOUNT_NAME = "default"


class CredentialStoreError(RuntimeError):
    pass


class CredentialStore:
    def get_api_key(self) -> Optional[str]:
        env_key = os.getenv(ENV_VAR)
        if env_key:
            return env_key

        backend = _load_backend()
        if backend is None:
            return None

        try:
            return backend.get_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception as exc:  # pragma: no cover - backend-specific
            raise CredentialStoreError(f"Unable to read API key from secure storage: {exc}") from exc

    def set_api_key(self, api_key: str) -> None:
        api_key = (api_key or "").strip()
        if not api_key:
            raise ValueError("API key is required.")

        backend = _require_backend()
        try:
            backend.set_password(SERVICE_NAME, ACCOUNT_NAME, api_key)
        except Exception as exc:  # pragma: no cover - backend-specific
            raise CredentialStoreError(f"Unable to store API key in secure storage: {exc}") from exc

    def delete_api_key(self) -> None:
        backend = _require_backend()
        try:
            backend.delete_password(SERVICE_NAME, ACCOUNT_NAME)
        except PasswordDeleteError:
            return
        except Exception as exc:  # pragma: no cover - backend-specific
            raise CredentialStoreError(f"Unable to delete API key from secure storage: {exc}") from exc

    def can_store_api_key(self) -> bool:
        return _load_backend() is not None


class PasswordDeleteError(RuntimeError):
    pass


class KeyringBackend:
    def __init__(self, keyring):
        self.keyring = keyring

    def get_password(self, service: str, account: str) -> Optional[str]:
        return self.keyring.get_password(service, account)

    def set_password(self, service: str, account: str, password: str) -> None:
        self.keyring.set_password(service, account, password)

    def delete_password(self, service: str, account: str) -> None:
        try:
            self.keyring.delete_password(service, account)
        except self.keyring.errors.PasswordDeleteError as exc:
            raise PasswordDeleteError(str(exc)) from exc


class WindowsCredentialBackend:
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", wintypes.LPVOID),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    PCREDENTIAL = ctypes.POINTER(CREDENTIAL)

    def __init__(self):
        self.advapi32 = ctypes.windll.advapi32
        self.kernel32 = ctypes.windll.kernel32

        self.advapi32.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(self.PCREDENTIAL),
        ]
        self.advapi32.CredReadW.restype = wintypes.BOOL
        self.advapi32.CredWriteW.argtypes = [ctypes.POINTER(self.CREDENTIAL), wintypes.DWORD]
        self.advapi32.CredWriteW.restype = wintypes.BOOL
        self.advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self.advapi32.CredDeleteW.restype = wintypes.BOOL
        self.advapi32.CredFree.argtypes = [wintypes.LPVOID]
        self.advapi32.CredFree.restype = None

    def get_password(self, service: str, account: str) -> Optional[str]:
        credential_pointer = self.PCREDENTIAL()
        ok = self.advapi32.CredReadW(
            _target_name(service, account),
            self.CRED_TYPE_GENERIC,
            0,
            ctypes.byref(credential_pointer),
        )
        if not ok:
            error = self.kernel32.GetLastError()
            if error == 1168:  # ERROR_NOT_FOUND
                return None
            raise ctypes.WinError(error)

        try:
            credential = credential_pointer.contents
            blob_size = int(credential.CredentialBlobSize)
            if blob_size <= 0:
                return None
            blob = ctypes.string_at(credential.CredentialBlob, blob_size)
            return blob.decode("utf-16-le")
        finally:
            self.advapi32.CredFree(credential_pointer)

    def set_password(self, service: str, account: str, password: str) -> None:
        blob = password.encode("utf-16-le")
        blob_buffer = ctypes.create_string_buffer(blob)
        credential = self.CREDENTIAL()
        credential.Type = self.CRED_TYPE_GENERIC
        credential.TargetName = _target_name(service, account)
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_byte))
        credential.Persist = self.CRED_PERSIST_LOCAL_MACHINE
        credential.UserName = account

        ok = self.advapi32.CredWriteW(ctypes.byref(credential), 0)
        if not ok:
            raise ctypes.WinError(self.kernel32.GetLastError())

    def delete_password(self, service: str, account: str) -> None:
        ok = self.advapi32.CredDeleteW(_target_name(service, account), self.CRED_TYPE_GENERIC, 0)
        if not ok:
            error = self.kernel32.GetLastError()
            if error == 1168:  # ERROR_NOT_FOUND
                raise PasswordDeleteError("Credential does not exist.")
            raise ctypes.WinError(error)


def _load_backend():
    try:
        import keyring
    except ImportError:
        keyring = None
    if keyring is not None:
        return KeyringBackend(keyring)

    if sys.platform == "win32":
        try:
            return WindowsCredentialBackend()
        except Exception:
            return None

    return None


def _require_backend():
    backend = _load_backend()
    if backend is None:
        raise CredentialStoreError(
            "Secure API key storage is unavailable. "
            f"You can still paste an API key for this FreeCAD session or set {ENV_VAR}."
        )
    return backend


def _target_name(service: str, account: str) -> str:
    return f"{service}:{account}"
