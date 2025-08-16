from pydantic import BaseModel, EmailStr, Field

class RegisterModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)

class LoginModel(BaseModel):
    email: EmailStr
    password: str

class OtpModel(BaseModel):
    email: EmailStr
    otpcode: str
    password: str