import os
import unittest
from unittest import mock

from orville_freecad.credentials import CredentialStore, ENV_VAR


class CredentialStoreTests(unittest.TestCase):
    def test_environment_api_key_takes_precedence(self):
        with mock.patch.dict(os.environ, {ENV_VAR: "env-secret"}):
            store = CredentialStore()

            self.assertEqual(store.get_api_key(), "env-secret")

    def test_missing_keyring_returns_none_when_no_env_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("orville_freecad.credentials._load_keyring", return_value=None):
                store = CredentialStore()

                self.assertIsNone(store.get_api_key())


if __name__ == "__main__":
    unittest.main()
