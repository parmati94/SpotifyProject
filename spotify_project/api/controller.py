from typing import Union
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
sys.path.append("..")
from ..main.helpers import *
from ..main.main import *
from ..main.config import *


app = FastAPI()
sp = spotify_auth()

origins = [
    "http://localhost:3000",  # React app's address
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    print('SP: {sp}')
    return {"Meow"}

@app.get("/get_all_playlists")
async def all_playlists():
    playlists = get_all_playlists()
    message = []
    for playlist in playlists:
        message.append(playlist["name"])
        
    return {"message": message}

@app.get("/validate_playlist")
async def validate_playlist(playlist_name):
    message = playlist_exists_with_id(playlist_name)
    return {"message": message}

@app.put("/add_daily")
async def daily_rec():
    date = get_date()
    name = create_daily_recommendation_playlist(date, 4)
    return {"message": name}

@app.put("/delete_daily")
async def delete_daily():
    message = delete_all_daily_playlists()
    return {"message": message}

@app.put("/create_playlist")
async def create_playlist(source_playlist, target_playlist):
    message = create_playlist_from_playlist(source_playlist, target_playlist)
    return {"message": message}