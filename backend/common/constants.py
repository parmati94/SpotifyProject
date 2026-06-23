"""App-wide constants."""

# Spotify OAuth scopes the app requests. Single source of truth shared by the
# login redirect and the token-refresh path.
SPOTIFY_SCOPE = (
    "user-library-read user-read-recently-played user-read-playback-state "
    "playlist-modify-private playlist-read-private playlist-read-collaborative "
    "user-top-read"
)

# Placeholder cover used when a playlist has no artwork.
DEFAULT_IMAGE_URL = "https://i.imgur.com/lBzb2v2.png"

# Stamped into the description of playlists this app creates (daily/weekly/created-from)
# so the UI can tell them apart from the user's own playlists. Spotify exposes no custom
# metadata, but `description` is writable and returned when listing — so it's our marker.
APP_PLAYLIST_MARKER = "Made with SpotifyProject"
