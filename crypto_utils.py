"""Small, real cryptographic helpers used by SecureAttendance."""

import hashlib
import hmac
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENVELOPE_VERSION = 1


def canonical_json(value: dict) -> bytes:
    """Serialize dictionaries consistently so HMAC input is reproducible."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def create_keys(secrets_dir: Path) -> None:
    """Create separate random AES and HMAC keys; never replace existing keys."""
    secrets_dir.mkdir(parents=True, exist_ok=True)
    try:
        secrets_dir.chmod(0o700)
    except OSError:
        pass
    enc_path = secrets_dir / "encryption.key"
    mac_path = secrets_dir / "hmac.key"
    if enc_path.exists() or mac_path.exists():
        raise FileExistsError("Key files already exist; refusing to replace them.")
    try:
        enc_path.write_bytes(os.urandom(32))
        mac_path.write_bytes(os.urandom(32))
        enc_path.chmod(0o600)
        mac_path.chmod(0o600)
    except OSError:
        for path in (enc_path, mac_path):
            try:
                path.unlink()
            except OSError:
                pass
        raise


def load_key(path: Path) -> bytes:
    """Load an existing 32-byte key or fail clearly; never regenerate it."""
    if not path.exists():
        raise FileNotFoundError(f"Required key is missing: {path}. Restore it from a secure backup; it will not be regenerated.")
    key = path.read_bytes()
    if len(key) != 32:
        raise ValueError(f"Key file must contain exactly 32 bytes: {path}")
    return key


def encrypt_bytes(plaintext: bytes, encryption_key: bytes, hmac_key: bytes) -> dict:
    """Encrypt using AES-256-GCM and authenticate the envelope with HMAC-SHA256."""
    nonce = os.urandom(12)
    ciphertext = AESGCM(encryption_key).encrypt(nonce, plaintext, None)
    envelope = {
        "version": ENVELOPE_VERSION,
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
    }
    envelope["hmac"] = hmac.new(hmac_key, canonical_json(envelope), hashlib.sha256).hexdigest()
    return envelope


def verify_envelope(envelope: dict, hmac_key: bytes) -> bool:
    """Check envelope format and HMAC before any decryption is attempted."""
    try:
        if set(envelope) != {"version", "nonce", "ciphertext", "hmac"}:
            return False
        if envelope["version"] != ENVELOPE_VERSION:
            return False
        bytes.fromhex(envelope["nonce"])
        bytes.fromhex(envelope["ciphertext"])
        supplied = envelope["hmac"]
        unsigned = {key: value for key, value in envelope.items() if key != "hmac"}
        expected = hmac.new(hmac_key, canonical_json(unsigned), hashlib.sha256).hexdigest()
        return isinstance(supplied, str) and hmac.compare_digest(expected, supplied)
    except (KeyError, TypeError, ValueError):
        return False


def decrypt_bytes(envelope: dict, encryption_key: bytes, hmac_key: bytes) -> bytes:
    """Verify HMAC first, then decrypt; reject any invalid or altered envelope."""
    if not verify_envelope(envelope, hmac_key):
        raise ValueError("Attendance integrity check failed; data was rejected.")
    try:
        return AESGCM(encryption_key).decrypt(bytes.fromhex(envelope["nonce"]), bytes.fromhex(envelope["ciphertext"]), None)
    except (InvalidTag, ValueError) as error:
        raise ValueError("Attendance could not be decrypted with this key.") from error
