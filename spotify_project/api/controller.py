import os
import sys
import logging
from os.path import join, dirname, exists
from typing import Union
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi import Depends
from fastapi import HTTPException
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from starlette.middleware.sessions import SessionMiddleware
from os.path import join, dirname
from dotenv import load_dotenv
sys.path.append("..")
from .models import Playlist
from ..main.operations import *
from ..main.main import *
from .auth import *

DEFAULT_IMAGE_URL = 'https://i.imgur.com/lBzb2v2.png'

class NoOpCacheHandler(spotipy.cache_handler.CacheHandler):
    def get_cached_token(self):
        return None

    def save_token_to_cache(self, token_info):
        pass


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="sovhioadufhg", https_only=False)
logging.basicConfig(level=logging.INFO)

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
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    print('SP: {sp}')
    return {"Meow"}

@app.get("/health_check")
async def health_check():
    print('Health check success.')
    return {"PING!"}

def get_spotify(request: Request) -> spotipy.Spotify:
    user_id = request.session.get("user_id")  # Get the user ID from the session
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token_info = request.session.get("token_info")
    if token_info is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    new_token_info = spotify_auth(token_info, user_id)
    if new_token_info != token_info:
        print('Access token refreshed.')
        request.session["token_info"] = new_token_info
    sp = spotipy.Spotify(auth=new_token_info['access_token'])
    return sp

@app.get("/login")
def login(request: Request):
    scope = "user-library-read user-read-recently-played user-read-playback-state playlist-modify-private " \
                "playlist-read-private playlist-read-collaborative user-top-read"
    sp_oauth = SpotifyOAuth(scope=scope, client_id=ID,
                            client_secret=SECRET,
                            redirect_uri=REDIRECT_URI)
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)

@app.get("/callback")
def callback(request: Request):
    scope = "user-library-read user-read-recently-played user-read-playback-state playlist-modify-private " \
            "playlist-read-private playlist-read-collaborative user-top-read"
    sp_oauth = SpotifyOAuth(scope=scope, client_id=ID,
                            client_secret=SECRET,
                            redirect_uri=REDIRECT_URI,
                            cache_handler=NoOpCacheHandler())
    code = request.query_params.get('code')
    token_info = sp_oauth.get_access_token(code)
    if 'access_token' not in token_info:
        # Redirect back to frontend with login=failure
        return RedirectResponse(url=f'{FRONTEND_URL}/?login=failure')
    request.session["token_info"] = token_info
    logging.info(f"Token info stored in session: {token_info}")
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_id = sp.current_user()['id']
    request.session["user_id"] = user_id
    
    cache_dir = join(dirname(__file__), 'cache')
    if not exists(cache_dir):
        os.makedirs(cache_dir)
    
    cache_path = join(cache_dir, f'.cache-{user_id}')
        
    sp_oauth = SpotifyOAuth(scope=scope, client_id=ID,
                            client_secret=SECRET,
                            redirect_uri=REDIRECT_URI,
                            cache_path=cache_path)
    sp_oauth._save_token_info(token_info)
    
    return RedirectResponse(url=f'{FRONTEND_URL}/?login=success')  # Redirect to the home page or any other page

@app.get("/check_session")
def check_session(request: Request):
    token_info = request.session.get("token_info")
    if token_info is None:
        return {"status": "error", "detail": "Not authenticated"}
    else:
        return {"status": "success", "user": "Authenticated"}

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    response = Response(content='{"message": "Logged out"}', media_type='application/json')
    return response

@app.get("/get_all_playlists")
async def all_playlists(request: Request, sp: spotipy.Spotify = Depends(get_spotify)):
    playlists = get_all_playlists(sp)
    message = []
    for playlist in playlists:
        try:
            message.append({
                "name": playlist["name"],
                "total_tracks": playlist["tracks"]["total"],
                "image_url": playlist["images"][0]["url"] if playlist["images"] else DEFAULT_IMAGE_URL
            })
        except Exception as e:
            print(f"Exception occurred with playlist: {playlist}")
            print(f"Exception: {e}")
        
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