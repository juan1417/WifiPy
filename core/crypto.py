import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


class KeyManager:
    def __init__(self, master_password: str, salt: bytes | None = None):
        self.salt = salt or os.urandom(16)
        self._key = self._derive_key(master_password, self.salt)
        self._cipher = Fernet(self._key)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = Argon2id(
            salt=salt,
            length=32,
            iterations=3,
            lanes=4,
            memory_cost=2**21,
        )
        derived = kdf.derive(password.encode())
        return base64.urlsafe_b64encode(derived)

    def encrypt(self, plaintext: str) -> bytes:
        return self._cipher.encrypt(plaintext.encode())

    def decrypt(self, token: bytes) -> str:
        return self._cipher.decrypt(token).decode()

    def rotate(self, new_password: str, old_token: bytes) -> bytes:
        new_salt = os.urandom(16)
        new_key = self._derive_key(new_password, new_salt)
        old_fernet = Fernet(self._key)
        new_fernet = Fernet(new_key)

        plaintext = old_fernet.decrypt(old_token)
        new_token = new_fernet.encrypt(plaintext)

        self.salt = new_salt
        self._key = new_key
        self._cipher = new_fernet
        return new_token

    def rotate_all(
        self, new_password: str, encrypted_tokens: list[bytes]
    ) -> list[bytes]:
        new_salt = os.urandom(16)
        new_key = self._derive_key(new_password, new_salt)
        new_fernet = Fernet(new_key)
        results = []
        for token in encrypted_tokens:
            plaintext = self._cipher.decrypt(token)
            results.append(new_fernet.encrypt(plaintext))
        self.salt = new_salt
        self._key = new_key
        self._cipher = new_fernet
        return results
