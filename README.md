# SpotifyProject

## Setup:

You will need to create a .env file which resides in the same directory as config.py (src/setup).  This file will need to include a CLIENT_SECRET, CLIENT_ID,
and a REDIRECT_URI, each on their own line.  These can be obtained by registering an app in the Spotify Developer Portal: https://developer.spotify.com/

## Usage:
Install dependencies:  
```pip install -r requirements.txt```

Run main.py to start program:  
```python -m spotify_project.main.main```

or Start FastAPI & React:  
```npm install```, then ```npm start```


Currently, this script has the ability to:

1. Create an 80-song playlist based on your top songs from the last month.
2. Extend a 'weekly playlist', which uses recommendations based on your top songs.  Will create one if it doesnt exist and populate with recommended songs.
3. Delete all of the daily playlists that were created for the day (from #1).
4. Create an 80 song playlist based off of an existing playlist.
5. Extend any existing playlist with either a) recommendations for you based on your top tracks or b) recommendations based on an existing playlist


