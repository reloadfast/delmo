from pydantic import BaseModel


class TorrentFileSchema(BaseModel):
    path: str
    size: int
    extension: str


class TorrentSchema(BaseModel):
    hash: str
    name: str
    save_path: str
    state: str
    progress: float
    files: list[TorrentFileSchema]
    tracker_domains: list[str]
