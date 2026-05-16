from typing import Literal

from pydantic import BaseModel, Field


UserRole = Literal["student", "instructor"]


class LoginRequest(BaseModel):
    username: str = Field(..., examples=["student"])
    password: str = Field(..., examples=["student123"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120, examples=["alice"])
    password: str = Field(..., min_length=6, examples=["alice123"])
    display_name: str = Field(..., min_length=1, max_length=200, examples=["Alice Student"])
    email: str | None = Field(default=None, max_length=255, examples=["alice@example.com"])
    student_id: str | None = Field(default=None, max_length=120, examples=["alice"])


class AuthenticatedUser(BaseModel):
    username: str = Field(..., examples=["student"])
    display_name: str = Field(..., examples=["Demo Student"])
    role: UserRole = Field(..., examples=["student"])
    student_id: str | None = Field(default=None, examples=["demo-student"])


class LoginResponse(BaseModel):
    success: bool = True
    access_token: str = Field(..., examples=["demo-student-token"])
    token_type: str = Field(default="bearer", examples=["bearer"])
    user: AuthenticatedUser
    message: str = Field(..., examples=["Login successful."])


class RegisterResponse(BaseModel):
    success: bool = True
    user: AuthenticatedUser
    message: str = Field(..., examples=["Registration successful."])


class AuthMeResponse(BaseModel):
    success: bool = True
    user: AuthenticatedUser
    message: str = Field(..., examples=["Authenticated user retrieved successfully."])
