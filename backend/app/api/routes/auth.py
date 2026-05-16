from fastapi import APIRouter, Depends, status

from app.core.auth import get_current_user
from app.schemas.auth import (
    AuthMeResponse,
    AuthenticatedUser,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(request: RegisterRequest) -> RegisterResponse:
    user_payload = register_user(
        username=request.username,
        password=request.password,
        display_name=request.display_name,
        email=request.email,
        student_id=request.student_id,
    )

    return RegisterResponse(
        user=AuthenticatedUser(**user_payload),
        message="Registration successful.",
    )


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    user_payload = authenticate_user(
        username=request.username,
        password=request.password,
    )

    access_token = user_payload.pop("access_token")

    return LoginResponse(
        access_token=access_token,
        user=AuthenticatedUser(**user_payload),
        message="Login successful.",
    )


@router.get("/me", response_model=AuthMeResponse)
def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthMeResponse:
    return AuthMeResponse(
        user=current_user,
        message="Authenticated user retrieved successfully.",
    )
