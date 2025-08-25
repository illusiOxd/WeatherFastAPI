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
    if users_collection.find_one({"email": registeruser.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    if users_collection.find_one({"username": registeruser.username}):
        raise HTTPException(status_code=400, detail="Username already registered")

    otp = str(random.randint(100000, 999999))
    send_otp_email(registeruser.email, otp)

    hashed_password = bcrypt.hashpw(registeruser.password.encode('utf-8'), bcrypt.gensalt())
    expires_at = datetime.datetime.now(datetime.timezone.utc) + timedelta(minutes=5)

    otp_collection.insert_one({
        "email": registeruser.email,
        "username": registeruser.username,
        "hashed_password": hashed_password,
        "otp": otp,
        "expires_at": expires_at
    })
    return {"message": "OTP sent to your email"}


@app.post("/verify_otp")
async def verify_otp(data: OtpModel):
    record = otp_collection.find_one({"email": data.email, "otp": data.otpcode})

    if not record:
        raise HTTPException(status_code=400, detail="Invalid code or expired, try again.")

    expires_at = record["expires_at"]
    # Если expires_at хранится без таймзоны, делаем его aware UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)

    if expires_at < datetime.datetime.now(datetime.timezone.utc):
        otp_collection.delete_one({"_id": record["_id"]})
        raise HTTPException(status_code=400, detail="Invalid code or expired, try again.")

    user = {
        "email": record["email"],
        "username": record["username"],
        "password_hashed": record["hashed_password"],
        "role": "user",
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = users_collection.insert_one(user)

    access_token = create_access_token({
        "sub": str(result.inserted_id),
        "email": user["email"],
        "username": user["username"],
        "role": user["role"]
    })

    otp_collection.delete_one({"_id": record["_id"]})

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/login")
async def login(login_data: LoginModel):
    user = users_collection.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not password_hash_check(login_data.password, user["password_hashed"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({
        "sub": str(user["_id"]),
        "email": user["email"],
        "username": user["username"],
        "role": user["role"]
    })

    return {"access_token": access_token, "token_type": "bearer"}


security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        username = payload.get("username")
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return {"user_id": user_id, "email": email, "username": username, "role": role}
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
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="City not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=503, detail="Weather service unavailable")

        data = response.json()

        weather_record = {
            "city": city,
            "temperature": data["main"]["temp"],
            "condition": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "feels_like": data["main"]["feels_like"],
            "requested_by": current_user["email"],
            "requested_at": datetime.datetime.now(datetime.timezone.utc)
        }
        weather_collection.insert_one(weather_record)

        return {
            "city": city,
            "temperature": data["main"]["temp"],
            "condition": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "feels_like": data["main"]["feels_like"]
        }

    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Weather service unavailable")
    except KeyError as e:
        raise HTTPException(status_code=502, detail=f"Invalid weather data: {str(e)}")


@app.get("/dbstatus")
async def get_dbstatus():
    stats = db.command("dbstats")
    return {"stats": stats}


@app.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=host, port=port)

# ПЛАНЫ ЧТО ДЕЛАТЬ ДАЛЬШЕ
# TODO: Добавить регистрацию и хранение пользователей с email/паролем или OAuth
# TODO: Привязывать прогноз погоды к конкретному пользователю
# TODO: Сохранять историю запросов каждого пользователя
# TODO: Добавить роли пользователей (админ/пользователь) с разными правами

# TODO: Сохранять дополнительные данные о погоде (влажность, ветер, прогноз на несколько дней)
# TODO: Возможность получать исторические данные о погоде из MongoDB
# TODO: Подписка на уведомления о погоде при изменении условий
# TODO: Поддержка нескольких источников данных для прогнозов

# TODO: Статистика количества запросов по городам
# TODO: Средняя температура по дням/месяцам
# TODO: Генерация графиков изменений погоды для фронтенда

# TODO: Ограничение частоты запросов (rate limiting)
# TODO: Логи запросов и ошибок с уровнем логирования
# TODO: Валидация входных данных (например, проверка корректности названия города)

# TODO: Разделение API на версии (/v1/forecast, /v2/forecast)
# TODO: Возможность фильтровать и сортировать данные из базы
# TODO: Добавить вебхуки для сторонних сервисов (например, уведомления в Telegram)