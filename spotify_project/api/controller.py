import os
import sys
import logging
from typing import Union
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi import Depends
from fastapi import HTTPException
from spotipy.oauth2 import SpotifyOAuth
from starlette.middleware.sessions import SessionMiddleware
from os.path import join, dirname
from dotenv import load_dotenv
sys.path.append("..")
from .models import Playlist
from ..main.helpers import *
from ..main.main import *
from ..main.config import *


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="sovhioadufhg")
logging.basicConfig(level=logging.INFO)
#sp = spotify_auth()

dotenv_path = join(dirname(dirname(__file__)), '.env')
load_dotenv(dotenv_path, override=True)

SECRET = os.getenv('CLIENT_SECRET')
ID = os.getenv('CLIENT_ID')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8000/callback')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# origins = [
#     "http://localhost:3000",  # React app's address
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    print('SP: {sp}')
    return {"Meow"}

def get_spotify(request: Request) -> spotipy.Spotify:
    #access_token = request.session.get("access_token")
    global access_token
    if access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sp = spotify_auth(access_token)
    return sp

@app.get("/login")
def login(request: Request):
    scope = "user-library-read user-read-recently-played user-read-playback-state playlist-modify-private " \
                "playlist-read-private playlist-read-collaborative user-top-read"
    sp_oauth = SpotifyOAuth(scope=scope, client_id=ID,
                            client_secret=SECRET,
                            redirect_uri=REDIRECT_URI,
                            cache_path=join(dirname(__file__), '.cache'))
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)

@app.get("/callback")
def callback(request: Request):
    global access_token
    scope = "user-library-read user-read-recently-played user-read-playback-state playlist-modify-private " \
            "playlist-read-private playlist-read-collaborative user-top-read"
    sp_oauth = SpotifyOAuth(scope=scope, client_id=ID,
                            client_secret=SECRET,
                            redirect_uri=REDIRECT_URI,
                            cache_path=join(dirname(__file__), '.cache'))
    code = request.query_params.get('code')
    token_info = sp_oauth.get_access_token(code)
    access_token = token_info['access_token']
    if 'access_token' not in token_info:
        # Redirect back to frontend with login=failure
        return RedirectResponse(url=f'{FRONTEND_URL}/?login=failure')
    # request.session["access_token"] = access_token
    logging.info(f"Access token stored in session: {access_token}")
    # access_token2 = request.session.get("access_token")
    # logging.info(f"Access token retrieved in callback: {access_token2}")
    return RedirectResponse(url=f'{FRONTEND_URL}/?login=success')  # Redirect to the home page or any other page

@app.get("/get_all_playlists")
async def all_playlists(request: Request, sp: spotipy.Spotify = Depends(get_spotify)):
    playlists = get_all_playlists(sp)
    message = []
    for playlist in playlists:
        message.append(playlist["name"])
        
    return {"message": message}

@app.get("/validate_playlist")
async def validate_playlist(playlist_name):
    message = playlist_exists_with_id(playlist_name)
    return {"message": message}

@app.put("/add_daily")
async def daily_rec(request: Request, sp: spotipy.Spotify = Depends(get_spotify)):
    date = get_date()
    name = create_daily_recommendation_playlist(date, 4, sp)
    return {"message": name}

@app.put("/add_weekly")
async def weekly_rec(request: Request, sp: spotipy.Spotify = Depends(get_spotify)):
    name = weekly_extended_playlist(sp)
    return {"message": name}

@app.put("/delete_daily")
async def delete_daily(request: Request, sp: spotipy.Spotify = Depends(get_spotify)):
    message = delete_all_daily_playlists(sp)
    return {"message": message}

@app.put("/create_playlist")
async def create_playlist(playlist: Playlist, sp: spotipy.Spotify = Depends(get_spotify)):
    message = create_playlist_from_playlist(playlist.source_playlist, playlist.target_playlist, playlist.num_songs, sp)
    return {"message": message}