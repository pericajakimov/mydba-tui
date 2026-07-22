"""Tests for password obfuscation."""

from mydba_tui.config.obfuscate import deobfuscate, obfuscate


def test_roundtrip_simple() -> None:
    """A password should survive obfuscate/deobfuscate roundtrip."""
    password = "MyS3cretP@ss!"
    stored = obfuscate(password)
    assert deobfuscate(stored) == password


def test_obfuscated_is_not_plaintext() -> None:
    """Obfuscated value should not contain the original password."""
    password = "cleartext_password"
    stored = obfuscate(password)
    assert password not in stored


def test_obfuscated_has_prefix() -> None:
    """Obfuscated values should start with 'obf:' prefix."""
    stored = obfuscate("test")
    assert stored.startswith("obf:")


def test_deobfuscate_legacy_plaintext() -> None:
    """Values without 'obf:' prefix should be returned as-is (backwards compat)."""
    assert deobfuscate("old_plaintext_password") == "old_plaintext_password"


def test_empty_string() -> None:
    """Empty passwords should stay empty."""
    assert obfuscate("") == ""
    assert deobfuscate("") == ""


def test_special_characters() -> None:
    """Passwords with special characters should roundtrip correctly."""
    passwords = [
        "P@ss:w0rd#!{2024}",
        'has"quotes"and\\slashes',
        "emoji_not_needed_but_works_™",
        "   spaces   ",
        "null",
        "obf:fake_prefix_in_password",
    ]
    for pwd in passwords:
        stored = obfuscate(pwd)
        assert deobfuscate(stored) == pwd, f"Failed for: {repr(pwd)}"
