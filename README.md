# SpotifyProject

## Setup:

The following dependencies are needed: <br />
spotipy - ```pip3 install spotipy``` <br />
dotenv - ```pip3 install python-dotenv```

Additionally, you will need to create a .env file which resides in the same directory as config.py (src/setup).  This file will need to include a CLIENT_SECRET, CLIENT_ID,
and a REDIRECT_URI, each on their own line.  These can be obtained by registering an app in the Spotify Developer Portal: https://developer.spotify.com/

## Usage:

Currently, this script has the ability to:

1. Create an 80-song playlist based on your top songs from the last month.
2. Extend a 'weekly playlist', which uses recommendations based on your top songs.  Will create one if it doesnt exist and populate with recommended songs.
3. Delete all of the daily playlists that were created for the day (from #1).
4. Create an 80 song playlist based off of an existing playlist.
5. Extend any existing playlist with either a) recommendations for you based on your top tracks or b) recommendations based on an existing playlist


