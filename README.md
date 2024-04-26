# SpotifyProject

## Setup:

You will need to create a .env file which resides in the spotify_project directory (see .env.example).  This file will need to include a CLIENT_SECRET and a CLIENT_ID, each on their own line.  These can be obtained by registering an app in the Spotify Developer Portal: https://developer.spotify.com/.

If you intend to simply run this without docker, your REDIRECT_URI will be hard set to http://localhost:8000/callback. Make sure to add this to 'Redirect URIs' in your Spotify Developer Portal by going to Dashboard ---> Settings.

## Usage:
Install dependencies:  
```pip install -r requirements.txt```

or Start FastAPI & React:  
```npm run setup```, then ```npm start```

## Docker
Since a `.env` is required with your own Spotify Developer credentials for the time being, you'll need to build both images locally:
```bash
docker build -t spotifyproject-frontend:latest -f ./client/Dockerfile ./client
docker build -t spotifyproject-api:latest -f ./spotify_project/Dockerfile ./spotify_project
```

The start the application with Docker Compose, use the provided docker-compose.yml.  Make sure to either fill in the placeholders manually, or set the intended values as environment variables on your machine prior to running docker-compose up.

Here are the environment variables you need to set:

- `API_HOST`: This should be the IP address of the machine where the API service will run. For example, `192.168.1.2`.

- `FRONTEND_HOST`: This should be the IP address of the machine where the frontend service will run. For example, `192.168.1.2`.

- `FRONTEND_PORT`: This is the port on your host machine that you want to use to access the frontend service. You can choose any port that is not being used by another service. For example, `3001`.

- `API_PORT`: This is the port on your host machine that you want to use to access the API service. You can choose any port that is not being used by another service. For example, `8001`.

The resulting `REDIRECT_URI` environment variable that is ultimately passed to the api container should also be added to 'Redirect URIs' in your Spotify Developer Portal Dashboard, under Dashboard --> Settings.  Using the above examples, you would add 'http://192.168.1.2:8001/callback'.  

## Functionalities

> **NOTE:** Some functionalities listed below were part of a previous iteration where the app was only a CLI interface. They have not yet been added to the UI/API.

This project currently supports the following features:

- **Playlist Creation:** 
  - Generate an 80-song playlist based on your top songs from the last month.
  - Create an 80-song playlist based on an existing playlist.

- **Playlist Extension:** 
  - Extend a 'weekly playlist' with recommendations based on your top songs. If it doesn't exist, the app will create one and populate it with recommended songs.
  - Extend any existing playlist with recommendations based on:
    - Your top tracks, or
    - An existing playlist.

- **Playlist Management:** 
  - Delete all of the daily playlists that were created for the day (from Playlist Creation feature).
