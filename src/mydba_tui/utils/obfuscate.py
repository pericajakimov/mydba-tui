"""
Simple password obfuscation.

Uses XOR with a machine-derived key and base64 encoding to avoid
storing passwords in plaintext. This is NOT cryptographic security —
it prevents casual reading of passwords in the YAML file.

Anyone with access to the machine and the source code can reverse this.
For production security, use .mylogin.cnf or prompt for passwords.
"""

import base64
import hashlib
import platform


def _get_machine_key() -> bytes:
    """Derive a repeatable key from machine-specific information.

    Uses the hostname and platform node as a seed. The key is the same
    across restarts on the same machine but differs between machines.

    Returns:
        32-byte key derived from machine identity.
    """
    seed = f"mydba:{platform.node()}:{platform.system()}"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR data with a repeating key.

    Args:
        data: Input bytes.
        key: Key bytes (repeated cyclically).

    Returns:
        XOR result.
    """
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def obfuscate(plaintext: str) -> str:
    """Obfuscate a password for storage.

    Args:
        plaintext: The password in clear text.

    Returns:
        Base64-encoded obfuscated string prefixed with 'obf:'.
    """
    if not plaintext:
        return ""
    key = _get_machine_key()
    xored = _xor_bytes(plaintext.encode("utf-8"), key)
    encoded = base64.b64encode(xored).decode("ascii")
    return f"obf:{encoded}"


def deobfuscate(stored: str) -> str:
    """Deobfuscate a stored password.

    Handles both obfuscated (prefixed with 'obf:') and legacy
    plaintext values for backwards compatibility.

    Args:
        stored: The stored value from profiles.yaml.

    Returns:
        The original plaintext password.
    """
    if not stored:
        return ""
    if not stored.startswith("obf:"):
        # Legacy plaintext — return as-is for backwards compatibility
        return stored
    encoded = stored[4:]
    key = _get_machine_key()
    xored = base64.b64decode(encoded)
    return _xor_bytes(xored, key).decode("utf-8")
