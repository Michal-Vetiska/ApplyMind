"""Auth request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    message: str
