"""In-memory vault session and machine-bound auto-unlock keyfile."""

from __future__ import annotations

import os
import socket
import time
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.vault.paths import auto_unlock_keyfile_path


class VaultSession:
    _key: Optional[bytes] = None
    _unlocked_at: Optional[float] = None
    _session_ttl: int = 86400

    DEFAULT_TTL = 3600
    EXTENDED_TTL = 86400

    @classmethod
    def unlock(cls, key: bytes, session_ttl: int = DEFAULT_TTL) -> None:
        cls._key = key
        cls._unlocked_at = time.time()
        cls._session_ttl = max(300, int(session_ttl))

    @classmethod
    def lock(cls) -> None:
        cls._key = None
        cls._unlocked_at = None
        cls._session_ttl = cls.DEFAULT_TTL

    @classmethod
    def is_unlocked(cls) -> bool:
        if cls._key is None:
            return False
        if time.time() - cls._unlocked_at > cls._session_ttl:
            cls.lock()
            return False
        return True

    @classmethod
    def get_key(cls) -> Optional[bytes]:
        if not cls.is_unlocked():
            return None
        cls._unlocked_at = time.time()
        return cls._key

    @classmethod
    def ttl_remaining(cls) -> int:
        if not cls.is_unlocked():
            return 0
        return max(0, int(cls._session_ttl - (time.time() - cls._unlocked_at)))


def _machine_identity() -> bytes:
    from pathlib import Path

    parts: list[str] = []
    machine_id_path = Path("/etc/machine-id")
    if machine_id_path.is_file():
        try:
            parts.append(machine_id_path.read_text(encoding="utf-8").strip())
        except OSError:
            pass
    parts.append(socket.gethostname())
    parts.append(str(os.getuid()))
    return "|".join(parts).encode("utf-8")


def _derive_wrapping_key(salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(_machine_identity())


def save_auto_unlock_keyfile(vault_key: bytes) -> None:
    path = auto_unlock_keyfile_path()
    salt = os.urandom(32)
    wrapping_key = _derive_wrapping_key(salt)
    nonce = os.urandom(12)
    aesgcm = AESGCM(wrapping_key)
    ciphertext = aesgcm.encrypt(nonce, vault_key, b"axon_vault_auto_unlock")
    path.write_bytes(salt + nonce + ciphertext)
    os.chmod(path, 0o600)


def load_auto_unlock_keyfile() -> Optional[bytes]:
    path = auto_unlock_keyfile_path()
    if not path.is_file():
        return None
    try:
        payload = path.read_bytes()
        if len(payload) < 44 + 16:
            return None
        salt = payload[:32]
        nonce = payload[32:44]
        ciphertext = payload[44:]
        wrapping_key = _derive_wrapping_key(salt)
        aesgcm = AESGCM(wrapping_key)
        return aesgcm.decrypt(nonce, ciphertext, b"axon_vault_auto_unlock")
    except Exception:
        return None


def remove_auto_unlock_keyfile() -> bool:
    path = auto_unlock_keyfile_path()
    if path.is_file():
        path.unlink()
        return True
    return False


def auto_unlock_enabled() -> bool:
    return auto_unlock_keyfile_path().is_file()
