import hashlib
import secrets
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import User
from app.db.session import session_scope


DEMO_USERS: dict[str, dict[str, Any]] = {
    "student": {
        "username": "student",
        "password": "student123",
        "display_name": "Demo Student",
        "role": "student",
        "student_id": "demo-student",
        "access_token": "demo-student-token",
    },
    "instructor": {
        "username": "instructor",
        "password": "instructor123",
        "display_name": "Demo Instructor",
        "role": "instructor",
        "student_id": None,
        "access_token": "demo-instructor-token",
    },
}

DEMO_TOKENS = {
    payload["access_token"]: username
    for username, payload in DEMO_USERS.items()
}

ACTIVE_TOKENS: dict[str, str] = {}

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260_000


def authenticate_user(username: str, password: str) -> dict[str, Any]:
    normalized_username = _normalize_username(username)

    demo_user = DEMO_USERS.get(normalized_username)

    if demo_user is not None:
        if secrets.compare_digest(password, str(demo_user["password"])):
            return _demo_user_payload(demo_user)

        raise _invalid_credentials()

    try:
        with session_scope() as db:
            user = db.get(User, normalized_username)

            if user is None:
                raise _invalid_credentials()

            if not bool(getattr(user, "is_active", True)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive.",
                )

            password_hash = getattr(user, "password_hash", None)

            if not password_hash or not verify_password(password, password_hash):
                raise _invalid_credentials()

            access_token = secrets.token_urlsafe(32)
            ACTIVE_TOKENS[access_token] = user.username

            return {
                **_user_payload(user),
                "access_token": access_token,
            }
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication database error: {exc}",
        ) from exc


def register_user(
    username: str,
    password: str,
    display_name: str,
    email: str | None = None,
    student_id: str | None = None,
) -> dict[str, Any]:
    normalized_username = _normalize_username(username)
    normalized_email = _normalize_optional(email)
    normalized_student_id = _normalize_optional(student_id) or normalized_username
    normalized_display_name = display_name.strip()

    if not normalized_username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username is required.",
        )

    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 6 characters.",
        )

    if not normalized_display_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Display name is required.",
        )

    if normalized_username in DEMO_USERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is reserved for demo login.",
        )

    try:
        with session_scope() as db:
            existing_user = db.get(User, normalized_username)

            if existing_user is not None and getattr(existing_user, "password_hash", None):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username is already registered.",
                )

            if normalized_email:
                email_owner = (
                    db.query(User)
                    .filter(User.email == normalized_email)
                    .one_or_none()
                )

                if email_owner is not None and email_owner.username != normalized_username:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email is already registered.",
                    )

            if existing_user is None:
                user = User(
                    username=normalized_username,
                    display_name=normalized_display_name,
                    role="student",
                    student_id=normalized_student_id,
                    email=normalized_email,
                    password_hash=hash_password(password),
                    is_active=True,
                )
                db.add(user)
            else:
                user = existing_user
                user.display_name = normalized_display_name
                user.role = "student"
                user.student_id = normalized_student_id
                user.email = normalized_email
                user.password_hash = hash_password(password)
                user.is_active = True

            db.flush()

            return _user_payload(user)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Registration database error: {exc}",
        ) from exc


def get_user_by_token(token: str) -> dict[str, Any]:
    demo_username = DEMO_TOKENS.get(token)

    if demo_username is not None:
        return _demo_user_payload(DEMO_USERS[demo_username], include_token=False)

    username = ACTIVE_TOKENS.get(token)

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        with session_scope() as db:
            user = db.get(User, username)

            if user is None:
                ACTIVE_TOKENS.pop(token, None)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication token.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not bool(getattr(user, "is_active", True)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive.",
                )

            return _user_payload(user)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication database error: {exc}",
        ) from exc


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()

    return (
        f"{PASSWORD_HASH_ALGORITHM}"
        f"${PASSWORD_HASH_ITERATIONS}"
        f"${salt}"
        f"${derived_key}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected_hash = password_hash.split("$", 3)
        iterations = int(iterations_raw)
    except ValueError:
        return False

    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()

    return secrets.compare_digest(actual_hash, expected_hash)


def _demo_user_payload(
    demo_user: dict[str, Any],
    include_token: bool = True,
) -> dict[str, Any]:
    payload = {
        "username": demo_user["username"],
        "display_name": demo_user["display_name"],
        "role": demo_user["role"],
        "student_id": demo_user["student_id"],
    }

    if include_token:
        payload["access_token"] = demo_user["access_token"]

    return payload


def _user_payload(user: User) -> dict[str, Any]:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "student_id": user.student_id,
    }


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    return normalized or None
