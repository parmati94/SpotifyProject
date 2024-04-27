from pydantic import BaseModel

class Playlist(BaseModel):
    source_playlist: str
    target_playlist: str