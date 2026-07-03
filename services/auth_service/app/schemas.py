import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from app.models import Role

USERNAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$"


def validate_new_password(password: str) -> str:
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain a lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain a digit")
    return password


NewPassword = Annotated[
    str,
    Field(min_length=8, max_length=128),
    AfterValidator(validate_new_password),
]
Username = Annotated[str, Field(pattern=USERNAME_PATTERN)]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictRequest):
    username: Username
    email: EmailStr
    password: NewPassword


class LoginRequest(StrictRequest):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class ProfileUpdateRequest(StrictRequest):
    current_password: str = Field(min_length=1, max_length=1024)
    username: Username | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def require_change(self) -> "ProfileUpdateRequest":
        if self.username is None and self.email is None:
            raise ValueError("At least one profile field is required")
        return self


class PasswordChangeRequest(StrictRequest):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: NewPassword


class PasswordConfirmationRequest(StrictRequest):
    current_password: str = Field(min_length=1, max_length=1024)


class AdminUserUpdateRequest(StrictRequest):
    role: Role | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "AdminUserUpdateRequest":
        if self.role is None and self.is_active is None:
            raise ValueError("At least one administrative field is required")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    role: Role
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class ErrorDetails(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetails


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
