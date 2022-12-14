import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os



def spotify_auth():
        scope = "user-library-read user-read-recently-played user-read-playback-state playlist-modify-private " \
                "playlist-read-private playlist-read-collaborative user-top-read"

        load_dotenv()

        SECRET = os.getenv('CLIENT_SECRET')
        ID = os.getenv('CLIENT_ID')
        REDIRECT_URI = os.getenv('REDIRECT_URI')

        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, client_id=ID,
                                                client_secret=SECRET,
                                                redirect_uri=REDIRECT_URI))

        return sp