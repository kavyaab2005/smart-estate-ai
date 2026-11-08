from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "buyer"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = ["buyer", "agent", "admin"]
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    user: UserResponse
    token: str

class OTPSendRequest(BaseModel):
    email: EmailStr


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str