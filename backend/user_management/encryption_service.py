import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_LEGACY_SALT = b'xiao-lee-salt_'
_SALT_SEPARATOR = ":"


class EncryptionService:

    def __init__(self, master_key: str):
        if not master_key:
            raise ValueError("ENCRYPTION_KEY cannot be empty.")
        self._master_key = master_key
        # Legacy fernet kept only for decrypting pre-existing data.
        self._legacy_fernet = Fernet(self._derive_key(_LEGACY_SALT))

    def _derive_key(self, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))

    def encrypt(self, data: str) -> str:
        """Encrypts a string. Output format: base64(salt):fernet_token"""
        if not isinstance(data, str):
            raise TypeError("Data to encrypt must be a string.")
        salt = os.urandom(16)
        fernet = Fernet(self._derive_key(salt))
        token = fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(salt).decode() + _SALT_SEPARATOR + token.decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypts a string. Handles both new (salt-prefixed) and legacy formats."""
        if not isinstance(encrypted_data, str):
            raise TypeError("Encrypted data must be a string.")
        if _SALT_SEPARATOR in encrypted_data:
            salt_b64, token = encrypted_data.split(_SALT_SEPARATOR, 1)
            salt = base64.urlsafe_b64decode(salt_b64)
            fernet = Fernet(self._derive_key(salt))
            return fernet.decrypt(token.encode()).decode()
        # Legacy format: static salt, no prefix
        return self._legacy_fernet.decrypt(encrypted_data.encode()).decode()
