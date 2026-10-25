"""Local user account registration and role-based session helpers."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

import streamlit as st

import database


def _password_digest(password: str, salt: bytes) -> bytes:
    """Hash a password with scrypt and a unique random salt."""
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)


def normalize_email(email: str) -> str:
    """Validate and normalize an email address for account identity."""
    normalized = email.strip().casefold()
    if len(normalized) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise ValueError("Enter a valid email address.")
    return normalized


def create_account(email: str, password: str, password_confirmation: str) -> None:
    """Create a standard User account after validating its email and password."""
    normalized_email = normalize_email(email)
    if len(password) < 12:
        raise ValueError("Use a password with at least 12 characters.")
    if len(password) > 1024:
        raise ValueError("Password must be 1024 characters or fewer.")
    if password != password_confirmation:
        raise ValueError("The passwords do not match.")
    salt = secrets.token_bytes(16)
    password_hash = _password_digest(password, salt)
    database.create_user_account(normalized_email, salt.hex(), password_hash.hex())


def authenticate(email: str, password: str) -> bool:
    """Verify credentials and start a regular User session."""
    normalized_email = normalize_email(email)
    if len(password) > 1024:
        return False
    account = database.get_user_account(normalized_email)
    if account is None:
        return False
    try:
        salt = bytes.fromhex(account["salt"])
        expected_hash = bytes.fromhex(account["password_hash"])
    except ValueError as exc:
        raise RuntimeError("The saved account credentials are invalid.") from exc
    if not hmac.compare_digest(_password_digest(password, salt), expected_hash):
        return False
    st.session_state["authenticated"] = True
    st.session_state["username"] = normalized_email
    st.session_state["role"] = "User"
    st.session_state["auth_method"] = "local"
    return True


def logout() -> None:
    """Clear the local authentication identity without disturbing app data."""
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.session_state["auth_method"] = None
