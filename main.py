import fastapi
import pymongo
import logging
import requests

from fastapi import FastAPI
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from keys.gitignorfile import uri, api_key, host, port

client = MongoClient(uri, server_api=ServerApi('1'))
db = client.weatherapp

weather_collection = db["forecasts"]
users_collection = db["users"]

app = FastAPI()

@app.get("/")
async def root():
    return {"server_status": "working"}

@app.get("/forecast/{city}")
async def get_forecast(city: str):
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