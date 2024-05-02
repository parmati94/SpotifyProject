from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from os.path import join, dirname
import os

def spotify_auth(token_info):
    scope = "user-library-read user-read-recently-played user-read-playback-state playlist-modify-private " \
            "playlist-read-private playlist-read-collaborative user-top-read"

    dotenv_path = join(dirname(dirname(__file__)), '.env')
    load_dotenv(dotenv_path)

    SECRET = os.getenv('CLIENT_SECRET')
    ID = os.getenv('CLIENT_ID')
    REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8000/callback')

    sp_oauth = SpotifyOAuth(scope=scope, client_id=ID,
                            client_secret=SECRET,
                            redirect_uri=REDIRECT_URI,
                            cache_path=join(dirname(__file__), '.cache'))
    
    if sp_oauth.is_token_expired(token_info):
        print("User token expired, refreshing")
        # Refresh the access token
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    
    return token_info