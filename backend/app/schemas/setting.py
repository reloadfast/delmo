from pydantic import BaseModel, field_validator


class SettingsResponse(BaseModel):
    """Flat key→value map of all settings."""

    model_config = {"from_attributes": True}

    data: dict[str, str]


class SettingsPatch(BaseModel):
    """Payload for PATCH /api/settings — upserts one or more key→value pairs."""

    updates: dict[str, str]

    @field_validator("updates")
    @classmethod
    def no_empty_keys(cls, v: dict[str, str]) -> dict[str, str]:
        for key in v:
            if not key.strip():
                raise ValueError("Setting keys must not be empty")
        return v
