"""Tests for authentication and role-based access control."""

import pytest
from fastapi import HTTPException

from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import (
    require_roles,
    get_current_user,
)


def test_admin_role_is_allowed():
    """ADMIN should be allowed when ADMIN is an accepted role."""
    role_checker = require_roles("ADMIN")

    current_user = {
        "sub": "1",
        "role": "ADMIN",
    }

    result = role_checker(current_user)

    assert result == current_user


def test_rescue_team_role_is_allowed():
    """RESCUE_TEAM should be allowed when RESCUE_TEAM is an accepted role."""
    role_checker = require_roles("RESCUE_TEAM")

    current_user = {
        "sub": "2",
        "role": "RESCUE_TEAM",
    }

    result = role_checker(current_user)

    assert result == current_user


def test_citizen_role_is_allowed():
    """CITIZEN should be allowed when CITIZEN is an accepted role."""
    role_checker = require_roles("CITIZEN")

    current_user = {
        "sub": "3",
        "role": "CITIZEN",
    }

    result = role_checker(current_user)

    assert result == current_user


def test_wrong_role_returns_403():
    """A user with the wrong role should receive HTTP 403."""
    role_checker = require_roles("ADMIN")

    current_user = {
        "sub": "4",
        "role": "CITIZEN",
    }

    with pytest.raises(HTTPException) as exc_info:
        role_checker(current_user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions"


def test_multiple_roles_are_supported():
    """A dependency can allow more than one role."""
    role_checker = require_roles("ADMIN", "RESCUE_TEAM")

    current_user = {
        "sub": "5",
        "role": "RESCUE_TEAM",
    }

    result = role_checker(current_user)

    assert result == current_user


def test_missing_role_returns_403():
    """A JWT without a role claim should be rejected."""
    role_checker = require_roles("ADMIN")

    current_user = {
        "sub": "6",
    }

    with pytest.raises(HTTPException) as exc_info:
        role_checker(current_user)

    assert exc_info.value.status_code == 403


def test_invalid_token_returns_401():
    """An invalid JWT should be rejected with HTTP 401."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid-token",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid or expired token"


def test_expired_or_invalid_token_cannot_access_role_checker():
    """An invalid JWT must fail before role authorization is evaluated."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid-token",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials)

    assert exc_info.value.status_code == 401

def test_incident_analyze_requires_authentication(client):
    """Incident analysis should reject requests without a JWT."""

    response = client.post(
        "/api/v1/incidents/analyze",
        json={
            "raw_text": "A building has collapsed and several people are trapped."
        },
    )

    assert response.status_code == 401

def test_incident_analyze_accepts_valid_citizen_token(client):
    """A valid CITIZEN JWT should pass the RBAC dependency."""

    from app.core.security import create_access_token

    token = create_access_token(
        subject="test-citizen",
        role="CITIZEN",
    )

    response = client.post(
        "/api/v1/incidents/analyze",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "raw_text": "A building has collapsed and several people are trapped."
        },
    )

    assert response.status_code != 401
    assert response.status_code != 403

def test_incident_analyze_accepts_valid_admin_token(client):
    """A valid ADMIN JWT should pass the RBAC dependency."""

    from app.core.security import create_access_token

    token = create_access_token(
        subject="test-admin",
        role="ADMIN",
    )

    response = client.post(
        "/api/v1/incidents/analyze",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "raw_text": "A building has collapsed and several people are trapped."
        },
    )

    assert response.status_code != 401
    assert response.status_code != 403


def test_incident_analyze_accepts_valid_rescue_team_token(client):
    """A valid RESCUE_TEAM JWT should pass the RBAC dependency."""

    from app.core.security import create_access_token

    token = create_access_token(
        subject="test-rescue",
        role="RESCUE_TEAM",
    )

    response = client.post(
        "/api/v1/incidents/analyze",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "raw_text": "A building has collapsed and several people are trapped."
        },
    )

    assert response.status_code != 401
    assert response.status_code != 403

def test_incident_analyze_rejects_unauthorized_role(client):
    """A valid JWT with an unauthorized role should receive HTTP 403."""

    from app.core.security import create_access_token

    token = create_access_token(
        subject="test-unauthorized",
        role="UNAUTHORIZED_ROLE",
    )

    response = client.post(
        "/api/v1/incidents/analyze",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "raw_text": "A building has collapsed and several people are trapped."
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_login_with_invalid_credentials_returns_401(client):
    """Invalid login credentials must not produce a JWT."""

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent-user@example.com",
            "password": "definitely-wrong-password",
            "requested_role": "ADMIN",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"