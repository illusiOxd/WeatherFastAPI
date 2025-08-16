import fastapi
import pymongo
import logging
import requests
import random
import datetime
from datetime import timedelta
import bcrypt
import jwt

from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# FROM PY FILES IMPORTS
from keys.gitignorfile import uri, api_key, host, port, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM
from pydantic_models.auth_models import RegisterModel, LoginModel, OtpModel
from services.smtp_service import send_otp_email
from functions.jwtfuncs import create_access_token

client = MongoClient(uri, server_api=ServerApi('1'))
db = client.weatherapp

# WEATHER MONGO DB
weather_collection = db["forecasts"]
users_collection = db["users"]
otp_collection = db["otps"]

app = FastAPI()

# USER AUTH LOGIC
isUserAuthenticated = False


# HASH CHECK
def password_hash_check(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

# WHOLE CRUD
@app.get("/")
async def root():
    return {"server_status": "working"}

# ПЛАНЫ ЧЁ ДЕЛАТЬ ВООБЩЕ
# 1. ПОСЛЕ ПРОВЕРКИ БАДИ ОТПРАВКА ОТП
# 2. ЕСЛИ ОТП СОВПАЛ, СОХРАНЕНИЕ ЮЗЕРА В КОЛЛЕКЦИИ В МОНГО
# 3. ПРИ ПОСЛЕДУЮЩЕМ ЛОГИНЕ ВЫДАЧА JWT ТОКЕНА И ПРОВЕРКА В ДРУГИХ ЭНДПОИНТАХ
# 4. ХУЙ ЕГО ЗНАЕТ ЧЁ ДАЛЬШЕ)))

@app.post("/register")
async def register(registeruser: RegisterModel):
    otp = str(random.randint(100000, 999999))
    send_otp_email(registeruser.email, otp)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + timedelta(minutes=5)
    otp_collection.insert_one({
        "email": registeruser.email,
        "otp": otp,
        "expires_at": expires_at
    })
    return {"message": "OTP sent to your email"}

@app.post("/verify_otp")
async def verify_otp(data: OtpModel):
    record = otp_collection.find_one({"email": data.email, "otp": data.otpcode})

    if not record:
        return {"message": "Invalid code or expired, try again."}

    expires_at = record["expires_at"]
    # Если expires_at хранится без таймзоны, делаем его aware UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)

    if expires_at < datetime.datetime.now(datetime.timezone.utc):
        return {"message": "Invalid code or expired, try again."}

    # Хэшируем пароль и создаём пользователя
    hashed_password = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt())
    user = {
        "email": data.email,
        "password_hashed": hashed_password,
        "role": "user",
        "logged_in": datetime.datetime.now(datetime.timezone.utc)
    }
    result = users_collection.insert_one(user)

    access_token = create_access_token({
        "sub": str(result.inserted_id),
        "email": user["email"],
        "role": user["role"]
    })

    otp_collection.delete_one({"email": data.email, "otp": data.otpcode})

    return {"access_token": access_token, "token_type": "bearer"}


security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return {"user_id": user_id, "email": email, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@app.get("/forecast/{city}")
async def get_forecast(city: str, current_user: dict = Depends(get_current_user)):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()

    weather_collection.insert_one({
        "city": city,
        "temperature": data["main"]["temp"],
        "condition": data["weather"][0]["description"],
    })
    return {"city": city, "status": "sent to mongodb", "temperature": data["main"]["temp"], "condition": data["weather"][0]["description"]}

@app.get("/dbstatus")
async def get_dbstatus():
    stats = db.command("dbstats")
    return {"stats": stats}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=host, port=port)

