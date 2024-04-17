# start_server.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run("spotify_project.api.controller:app", host="127.0.0.1", port=8000, reload=True)