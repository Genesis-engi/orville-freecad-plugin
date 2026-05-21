"""Secure API key storage for the Orville FreeCAD workbench."""

from __future__ import annotations

import os
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

        keyring = _load_keyring()
        if keyring is None:
            return None

        try:
            return keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception as exc:  # pragma: no cover - backend-specific
            raise CredentialStoreError(f"Unable to read API key from keyring: {exc}") from exc

    def set_api_key(self, api_key: str) -> None:
        api_key = (api_key or "").strip()
        if not api_key:
            raise ValueError("API key is required.")

        keyring = _require_keyring()
        try:
            keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, api_key)
        except Exception as exc:  # pragma: no cover - backend-specific
            raise CredentialStoreError(f"Unable to store API key in keyring: {exc}") from exc

    def delete_api_key(self) -> None:
        keyring = _require_keyring()
        try:
            keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
        except keyring.errors.PasswordDeleteError:
            return
        except Exception as exc:  # pragma: no cover - backend-specific
            raise CredentialStoreError(f"Unable to delete API key from keyring: {exc}") from exc

    def can_store_api_key(self) -> bool:
        return _load_keyring() is not None


def _load_keyring():
    try:
        import keyring
    except ImportError:
        return None
    return keyring


def _require_keyring():
    keyring = _load_keyring()
    if keyring is None:
        raise CredentialStoreError(
            "The Python keyring package is required to store API keys securely. "
            f"You can still use {ENV_VAR} for this FreeCAD session."
        )
    return keyring
