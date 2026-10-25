"""Small role-based demo authentication for the PharmaGuard prototype."""

from __future__ import annotations

import hashlib
import hmac

import streamlit as st

# Demo-only credentials. Replace these with managed identity and hashed secrets
# from a secure secrets store before deploying to a real clinical environment.
_SALT = b"pharmaguard-demo-only"
_ACCOUNTS = {
    "admin": ("Admin", "admin123"),
    "user": ("User", "user123"),
}


def _password_digest(password: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _SALT, 120_000)


def authenticate(username: str, password: str, requested_role: str) -> bool:
    """Authenticate a demo account and persist its role in Streamlit session state."""
    account = _ACCOUNTS.get(username.strip().casefold())
    if account is None:
        return False
    role, expected_password = account
    if role != requested_role or not hmac.compare_digest(
        _password_digest(password), _password_digest(expected_password)
    ):
        return False
    st.session_state["authenticated"] = True
    st.session_state["username"] = username.strip()
    st.session_state["role"] = role
    return True


def logout() -> None:
    """Clear authentication identity without disturbing other application state."""
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["role"] = None
