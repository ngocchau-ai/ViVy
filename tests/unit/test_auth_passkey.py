"""
Unit tests for User Authentication, JWT Tokens, Session Invalidation & WebAuthn 1-Touch Passkey Login.
"""

import time
import pytest
from vivy.auth.user_manager import UserAuthenticationManager
from vivy.auth.webauthn_passkey import WebAuthnPasskeyManager


def test_user_authentication_manager():
    auth_mgr = UserAuthenticationManager(db_path=":memory:")
    user = auth_mgr.register_user(username="ngocchau", password="secure_password_2026", role="admin")

    assert user.username == "ngocchau"
    assert user.role == "admin"

    # Authenticate valid credentials
    auth_user = auth_mgr.authenticate_user("ngocchau", "secure_password_2026")
    assert auth_user is not None
    assert auth_user.username == "ngocchau"

    # Authenticate invalid credentials
    invalid_user = auth_mgr.authenticate_user("ngocchau", "wrong_password")
    assert invalid_user is None

    # JWT Token creation & verification
    token = auth_mgr.create_jwt_token(user)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    payload = auth_mgr.verify_jwt_token(token)
    assert payload is not None
    assert payload["sub"] == "ngocchau"


def test_session_invalidation_revoke_all():
    auth_mgr = UserAuthenticationManager(db_path=":memory:")
    user = auth_mgr.register_user(username="trader_bob", password="password_123", role="trader")

    # Issued old token
    old_token = auth_mgr.create_jwt_token(user)
    assert auth_mgr.verify_jwt_token(old_token) is not None

    # Execute session invalidation
    time.sleep(0.01)
    auth_mgr.revoke_all_sessions()

    # Old token must now be rejected
    assert auth_mgr.verify_jwt_token(old_token) is None

    # New token issued after invalidation must be accepted
    new_token = auth_mgr.create_jwt_token(user)
    assert auth_mgr.verify_jwt_token(new_token) is not None


def test_webauthn_passkey_manager():
    passkey_mgr = WebAuthnPasskeyManager(rp_name="ViVy AI Test")
    reg_opts = passkey_mgr.generate_registration_options("trader_alex")

    assert reg_opts.user_name == "trader_alex"
    assert len(reg_opts.challenge) == 64

    login_opts = passkey_mgr.generate_assertion_options("trader_alex")
    assert "challenge" in login_opts

    verified = passkey_mgr.verify_1touch_login(login_opts["challenge"], {})
    assert verified is True
