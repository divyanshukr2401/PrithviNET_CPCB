"""Simple application auth and role/session helpers for PRITHVINET."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import secrets
import uuid
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException

from app.core.config import settings
from app.models.schemas import (
    AuthenticatedUser,
    AuthResponse,
    CitizenAccessRequest,
    LoginRequest,
    UserRole,
)
from app.services.ingestion.postgres_writer import pg_writer


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _urlsafe_b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _urlsafe_b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode())


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120000,
    )
    return _urlsafe_b64(digest)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{salt}${_hash_password(password, salt)}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, digest = stored_hash.split("$", 1)
    calculated = _hash_password(password, salt)
    return hmac.compare_digest(calculated, digest)


def _sign_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    raw_b64 = _urlsafe_b64(raw)
    signature = hmac.new(
        settings.APP_AUTH_SECRET.encode(),
        raw_b64.encode(),
        hashlib.sha256,
    ).digest()
    return f"{raw_b64}.{_urlsafe_b64(signature)}"


def _unsign_payload(token: str) -> dict:
    try:
        raw_b64, sig_b64 = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid auth token") from exc

    expected_sig = hmac.new(
        settings.APP_AUTH_SECRET.encode(),
        raw_b64.encode(),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_urlsafe_b64(expected_sig), sig_b64):
        raise HTTPException(status_code=401, detail="Invalid auth token")

    payload = json.loads(_urlsafe_b64_decode(raw_b64))
    expires_at = datetime.fromisoformat(payload["exp"])
    if expires_at < _now_utc():
        raise HTTPException(status_code=401, detail="Session expired")
    return payload


def _role_home(role: UserRole) -> str:
    if role == UserRole.CITIZEN:
        return "/gamification"
    if role == UserRole.INDUSTRY_USER:
        return "/compliance"
    return "/"


def _user_from_row(row: dict) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=row["user_id"],
        username=row["username"],
        full_name=row.get("full_name") or row["username"],
        role=UserRole(row.get("role") or UserRole.CITIZEN.value),
        email=row.get("email"),
        phone=row.get("phone"),
        city=row.get("city"),
        state=row.get("state"),
        is_active=bool(row.get("is_active", True)),
        auth_mode=row.get("auth_mode") or "password",
        assigned_region=row.get("assigned_region"),
        assigned_state=row.get("assigned_state"),
        assigned_district=row.get("assigned_district"),
        industry_scope=row.get("industry_scope"),
    )


class AuthService:
    INTERNAL_USERS = [
        {
            "user_id": "AUTH-SUPER-001",
            "username": "super.admin",
            "email": "super.admin@prithvinet.gov.in",
            "full_name": "Super Administrator",
            "role": UserRole.SUPER_ADMIN.value,
            "password": "superadmin123",
            "assigned_region": "All India",
            "assigned_state": "All India",
        },
        {
            "user_id": "AUTH-REGION-001",
            "username": "regional.officer.cg",
            "email": "regional.officer@prithvinet.gov.in",
            "full_name": "Regional Officer, Chhattisgarh",
            "role": UserRole.REGIONAL_OFFICER.value,
            "password": "regional123",
            "assigned_region": "Central India",
            "assigned_state": "Chhattisgarh",
        },
        {
            "user_id": "AUTH-MONITOR-001",
            "username": "monitoring.team",
            "email": "monitoring.team@prithvinet.gov.in",
            "full_name": "Monitoring Team Console",
            "role": UserRole.MONITORING_TEAM.value,
            "password": "monitor123",
            "assigned_state": "Chhattisgarh",
        },
        {
            "user_id": "AUTH-IND-001",
            "username": "industry.user",
            "email": "industry.user@prithvinet.gov.in",
            "full_name": "Industry User Demo",
            "role": UserRole.INDUSTRY_USER.value,
            "password": "industry123",
            "assigned_state": "Chhattisgarh",
            "assigned_district": "Raipur",
            "industry_scope": "Jayaswal Neco Industries Limited",
        },
    ]

    async def ensure_seed_users(self) -> None:
        for user in self.INTERNAL_USERS:
            await pg_writer.create_or_update_internal_user(
                user_id=user["user_id"],
                username=user["username"],
                email=user.get("email"),
                full_name=user["full_name"],
                role=user["role"],
                password_hash=hash_password(user["password"]),
                state=user.get("assigned_state"),
                assigned_region=user.get("assigned_region"),
                assigned_state=user.get("assigned_state"),
                assigned_district=user.get("assigned_district"),
                industry_scope=user.get("industry_scope"),
            )

    def _issue_token(self, user: AuthenticatedUser) -> AuthResponse:
        expires_at = _now_utc() + timedelta(hours=settings.AUTH_TOKEN_EXPIRE_HOURS)
        token = _sign_payload(
            {
                "sub": user.user_id,
                "role": user.role.value,
                "exp": expires_at.isoformat(),
            }
        )
        return AuthResponse(
            access_token=token,
            expires_at=expires_at,
            user=user,
            role_home=_role_home(user.role),
        )

    async def login(self, payload: LoginRequest) -> AuthResponse:
        row = await pg_writer.get_user_by_identity(payload.username_or_email)
        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if row.get("role") != payload.role.value:
            raise HTTPException(
                status_code=403, detail="Role mismatch for this account"
            )
        if not verify_password(payload.password, row.get("password_hash")):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user = _user_from_row(row)
        await pg_writer.update_user_last_login(user.user_id)
        return self._issue_token(user)

    async def citizen_continue(self, payload: CitizenAccessRequest) -> AuthResponse:
        base = _slug_username(payload.full_name, payload.city)
        existing = await pg_writer.get_user_by_identity(base)
        user_id = (
            existing["user_id"]
            if existing and existing.get("role") == UserRole.CITIZEN.value
            else f"CIT-{uuid.uuid4().hex[:10].upper()}"
        )
        row = await pg_writer.upsert_citizen_user(
            user_id=user_id,
            username=base,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            city=payload.city,
            state=payload.state,
        )
        user = _user_from_row(row)
        await pg_writer.update_user_last_login(user.user_id)
        return self._issue_token(user)

    async def resolve_user(self, token: str) -> AuthenticatedUser:
        payload = _unsign_payload(token)
        row = await pg_writer.get_user(payload["sub"])
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        user = _user_from_row(row)
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is inactive")
        return user

    def refresh_session(self, user: AuthenticatedUser) -> AuthResponse:
        return self._issue_token(user)


def _slug_username(full_name: str, city: str) -> str:
    seed = f"{full_name} {city}".lower()
    cleaned = "".join(ch if ch.isalnum() else "." for ch in seed)
    cleaned = ".".join(part for part in cleaned.split(".") if part)
    return cleaned[:60] or f"citizen.{uuid.uuid4().hex[:6]}"


auth_service = AuthService()


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    auth_cookie: Optional[str] = Cookie(default=None, alias="prithvinet_auth_token"),
) -> AuthenticatedUser:
    token: Optional[str] = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif auth_cookie:
        token = auth_cookie

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await auth_service.resolve_user(token)


def require_roles(*roles: UserRole):
    allowed = {role.value for role in roles}

    async def dependency(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if user.role.value not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return user

    return dependency
