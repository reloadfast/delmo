from pydantic import BaseModel, Field


class ConnectionStatusResponse(BaseModel):
    connected: bool
    daemon_version: str | None = None
    error: str | None = None


class ConnectionTestRequest(BaseModel):
    host: str = Field(..., min_length=1)
    port: int = Field(default=58846, ge=1, le=65535)
    username: str = ""
    password: str = ""
