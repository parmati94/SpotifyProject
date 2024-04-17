import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from os.path import join, dirname
import os



def spotify_auth():
        scope = "user-library-read user-read-recently-played user-read-playback-state playlist-modify-private " \
                "playlist-read-private playlist-read-collaborative user-top-read"

        dotenv_path = join(dirname(dirname(__file__)), '.env')
        print(dotenv_path)
        load_dotenv(dotenv_path)

        SECRET = os.getenv('CLIENT_SECRET')
        ID = os.getenv('CLIENT_ID')
        print(ID)
        REDIRECT_URI = os.getenv('REDIRECT_URI')

        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, client_id=ID,
                                                client_secret=SECRET,
                                                redirect_uri=REDIRECT_URI,
                                                cache_path=join(dirname(__file__), '.cache')))
        
        
        #keeping this here for later
        #spotipy.SpotifyOAuth.get_access_token(request.args.get("code"))

        return sp