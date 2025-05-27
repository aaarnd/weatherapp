from fastapi import FastAPI, HTTPException, Cookie, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
import requests
import translators as ts
import uuid


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_history: Dict[str, list] = {}
cities_count: Dict[str, int] = {}


class City(BaseModel):
    name: str


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/weather")
def get_weather(
    city: str, response: JSONResponse, session_id: Optional[str] = Cookie(default=None)
):
    city = ts.translate_text(
        city, translator="google", from_language="ru", to_language="en"
    )

    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(key="session_id", value=session_id)

    response.set_cookie(key="city", value=city)

    if session_id not in user_history:
        user_history[session_id] = []
    user_history[session_id].append(city)

    cities_count[city] = cities_count.get(city, 0) + 1

    fetch_coords_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
    response = requests.get(fetch_coords_url)
    if response.status_code != 200:
        print(response)
        print(response.content)
        raise HTTPException(
            status_code=500, detail="Ошибка при получении координат города"
        )

    data = response.json()

    latitude = data["results"][0]["latitude"]
    longitude = data["results"][0]["longitude"]

    fetch_weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Europe/Moscow&forecast_days=3"
    weather_response = requests.get(fetch_weather_url)
    return weather_response.json()


@app.get("/apiv1/history")
def get_user_history(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session_id cookie provided")
    history = user_history.get(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"history": history}


@app.get("/apiv1/cities")
def get_cities_count():
    return cities_count
