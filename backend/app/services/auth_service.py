from fastapi import HTTPException, status


DEMO_USERS = {
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


def authenticate_user(username: str, password: str) -> dict:
    """
    Demo authentication / demo kimlik doğrulama.

    This is intentionally simple for the graduation project demo.
    It is not a production-grade authentication system.
    """

    user = DEMO_USERS.get(username)

    if user is None or user["password"] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    return _public_user_payload(user)


def get_user_by_token(access_token: str) -> dict:
    for user in DEMO_USERS.values():
        if user["access_token"] == access_token:
            return _public_user_payload(user)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
    )


def _public_user_payload(user: dict) -> dict:
    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "student_id": user["student_id"],
        "access_token": user["access_token"],
    }
