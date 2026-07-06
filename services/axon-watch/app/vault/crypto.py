"""AES-256-GCM vault crypto and TOTP helpers (Signal-compatible)."""

from __future__ import annotations

import base64
import hashlib
import io
import os

import pyotp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 480_000
VERIFY_SALT = b"devbrain_vault_verify"


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def hash_password_for_storage(password: str, salt: bytes) -> str:
    key = derive_key(password, salt)
    return hashlib.sha256(key + VERIFY_SALT).hexdigest()


def encrypt(plaintext: str, key: bytes) -> str:
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(encoded: str, key: bytes) -> str:
    combined = base64.b64decode(encoded.encode("ascii"))
    nonce = combined[:12]
    ciphertext = combined[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, account_name: str = "Axon Secure Vault") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name="Axon")


def generate_qr_data_uri(secret: str) -> str:
    try:
        import qrcode

        uri = get_totp_uri(secret)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=2,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
    except Exception:
        return ""


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)
