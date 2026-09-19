
from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str

    # Signup is now a single step with no email verification, so reject the
    # inputs that would otherwise surface as a 500 / an unusable account:
    # empty values, a display name longer than its DB column, and passwords
    # over bcrypt's 72-byte limit (bcrypt raises rather than truncating).
    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password cannot be empty")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Display name cannot be empty")
        if len(v) > 100:
            raise ValueError("Display name must be at most 100 characters")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class GuestAuthResponse(BaseModel):
    access_token: str
    token_type: str
    guest_id: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str

class UpdateProfileRequest(BaseModel):
    display_name: str
