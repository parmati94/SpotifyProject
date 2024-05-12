from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from os.path import join, dirname, exists
import os

def spotify_auth(token_info, user_id):
    scope = "user-library-read user-read-recently-played user-read-playback-state playlist-modify-private " \
            "playlist-read-private playlist-read-collaborative user-top-read"

    dotenv_path = join(dirname(dirname(__file__)), '.env')
    load_dotenv(dotenv_path)

    SECRET = os.getenv('CLIENT_SECRET')
    ID = os.getenv('CLIENT_ID')
    REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8000/callback')
    
    cache_dir = join(dirname(__file__), 'cache')
    if not exists(cache_dir):
        os.makedirs(cache_dir)
    
    cache_path = join(cache_dir, f'.cache-{user_id}')

    sp_oauth = SpotifyOAuth(scope=scope, client_id=ID,
                            client_secret=SECRET,
                            redirect_uri=REDIRECT_URI,
                            cache_path=cache_path)
    
    if sp_oauth.is_token_expired(token_info):
        print("User token expired, refreshing")
        # Refresh the access token
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    
    return token_info